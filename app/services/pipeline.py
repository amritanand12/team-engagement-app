"""
Orchestrates the full daily run: scan -> render -> send individual emails ->
build & send the team digest. This is the single entry point called by both
the scheduler and the manual admin-trigger endpoint, so "run it now" and
"run it via cron" always take the identical code path.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DigestLog, DigestStatus, EmployeeProfile, EventLog, EventStatus, Organization
from app.services import digest as digest_service
from app.services import scanner
from app.services.mailer import BaseMailer, get_mailer, send_with_retry
from app.services.renderer import render_event

logger = logging.getLogger("engagement.pipeline")
settings = get_settings()


@dataclass
class PipelineResult:
    batch_id: str
    detected: int
    rendered: int
    sent: int
    failed: int
    skipped: int
    digest_status: str


def _render_pending(db: Session, batch_id: str, organization_id: str | None = None) -> None:
    """
    Renders anything not yet rendered: fresh PENDING rows, plus any row that
    previously FAILED at the rendering stage (no rendered_html yet).
    """
    q = db.query(EventLog).filter(
        EventLog.batch_id == batch_id,
        EventLog.status.in_([EventStatus.PENDING, EventStatus.FAILED]),
        EventLog.rendered_html.is_(None),
    )
    if organization_id:
        q = q.filter(EventLog.organization_id == organization_id)

    candidates = q.all()
    for event in candidates:
        render_event(db, event)
    db.flush()


def _send_individual_emails(
    db: Session, batch_id: str, mailer: BaseMailer, organization_id: str | None = None
) -> None:
    """
    Sends anything rendered-but-not-sent for this batch and organization.
    """
    q = db.query(EventLog).filter(
        EventLog.batch_id == batch_id,
        EventLog.status.in_([EventStatus.RENDERED, EventStatus.FAILED]),
        EventLog.rendered_html.isnot(None),
    )
    if organization_id:
        q = q.filter(EventLog.organization_id == organization_id)

    rendered = q.all()

    for event in rendered:
        employee = event.employee or db.get(EmployeeProfile, event.employee_id)
        if employee is None or not employee.email:
            event.status = EventStatus.FAILED
            event.error_detail = "Employee has no email address"
            continue

        event.attempt_count += 1
        success, error = send_with_retry(mailer, employee.email, event.rendered_subject, event.rendered_html)
        if success:
            event.status = EventStatus.SENT
            from datetime import datetime
            event.sent_at = datetime.utcnow()
            event.error_detail = None
        else:
            event.status = EventStatus.FAILED
            event.error_detail = error

    db.flush()


def _send_digest(
    db: Session,
    batch_id: str,
    batch_date: date,
    mailer: BaseMailer,
    org: Organization | None = None,
) -> str:
    org_id = org.id if org else None
    events = digest_service.get_renderable_events_for_batch(db, batch_id, organization_id=org_id)

    q = db.query(DigestLog).filter(DigestLog.batch_id == batch_id)
    if org_id:
        q = q.filter(DigestLog.organization_id == org_id)
    existing = q.first()

    if existing and existing.status == DigestStatus.SENT:
        # Already sent for this batch — never double-post the team digest.
        return existing.status.value

    channel_id = (org.digest_channel_id if org else None) or settings.DEFAULT_DIGEST_CHANNEL_ID
    company_name = (org.name if org else None) or settings.COMPANY_NAME
    company_logo = (org.company_logo_url if org else None) or settings.COMPANY_LOGO_URL

    if not events:
        log = existing or DigestLog(
            organization_id=org.id if org else "default",
            batch_id=batch_id,
            channel_id=channel_id,
        )
        log.status = DigestStatus.EMPTY_SKIPPED
        log.event_count = 0
        if not existing:
            db.add(log)
        db.flush()
        return log.status.value

    html = digest_service.render_digest(
        events, batch_date, company_name=company_name, company_logo_url=company_logo
    )

    log = existing or DigestLog(
        organization_id=org.id if org else "default",
        batch_id=batch_id,
        channel_id=channel_id,
    )
    log.rendered_html = html
    log.event_count = len(events)

    success, error = send_with_retry(
        mailer, channel_id, f"Celebrations today at {company_name}", html
    )
    if success:
        log.status = DigestStatus.SENT
        from datetime import datetime
        log.sent_at = datetime.utcnow()
        log.error_detail = None
    else:
        log.status = DigestStatus.FAILED
        log.error_detail = error

    if not existing:
        db.add(log)
    db.flush()
    return log.status.value


def run_tenant_pipeline(
    db: Session,
    organization_id: str,
    scan_date: date | None = None,
    mailer: BaseMailer | None = None,
) -> PipelineResult:
    """Runs the full scan -> render -> send -> digest pipeline for a single tenant."""
    scan_date = scan_date or date.today()
    org = db.get(Organization, organization_id)
    mailer = mailer or get_mailer(org)
    leap_policy = org.leap_day_policy if org else settings.LEAP_DAY_POLICY

    detected, batch_id = scanner.run_scan(
        db, scan_date, organization_id=organization_id, leap_day_policy=leap_policy
    )
    db.commit()

    _render_pending(db, batch_id, organization_id=organization_id)
    db.commit()

    _send_individual_emails(db, batch_id, mailer, organization_id=organization_id)
    db.commit()

    digest_status = _send_digest(db, batch_id, scan_date, mailer, org=org)
    db.commit()

    counts = {
        EventStatus.SENT: 0,
        EventStatus.FAILED: 0,
        EventStatus.SKIPPED: 0,
        EventStatus.RENDERED: 0,
    }
    rows = (
        db.query(EventLog.status)
        .filter(EventLog.batch_id == batch_id, EventLog.organization_id == organization_id)
        .all()
    )
    for (status,) in rows:
        counts[status] = counts.get(status, 0) + 1

    result = PipelineResult(
        batch_id=batch_id,
        detected=len(rows),
        rendered=counts.get(EventStatus.SENT, 0) + counts.get(EventStatus.RENDERED, 0),
        sent=counts.get(EventStatus.SENT, 0),
        failed=counts.get(EventStatus.FAILED, 0),
        skipped=counts.get(EventStatus.SKIPPED, 0),
        digest_status=digest_status,
    )
    logger.info("Pipeline complete for org %s batch %s: %s", organization_id, batch_id, result)
    return result


def run_daily_pipeline(
    db: Session,
    scan_date: date | None = None,
    mailer: BaseMailer | None = None,
    organization_id: str | None = None,
) -> PipelineResult:
    """
    Main pipeline entrypoint. If organization_id is provided, runs for that tenant.
    Otherwise runs for all active organizations.
    """
    scan_date = scan_date or date.today()
    mailer = mailer or get_mailer()

    if organization_id:
        return run_tenant_pipeline(db, organization_id, scan_date=scan_date, mailer=mailer)

    orgs = db.query(Organization).filter(Organization.is_active == True).all()
    if not orgs:
        logger.info("No active organizations found. Skipping daily pipeline.")
        return PipelineResult(
            batch_id=scan_date.isoformat(),
            detected=0,
            rendered=0,
            sent=0,
            failed=0,
            skipped=0,
            digest_status=DigestStatus.EMPTY_SKIPPED.value,
        )

    last_result = None
    for org in orgs:
        last_result = run_tenant_pipeline(db, org.id, scan_date=scan_date, mailer=mailer)

    return last_result or PipelineResult(
        batch_id=scan_date.isoformat(),
        detected=0,
        rendered=0,
        sent=0,
        failed=0,
        skipped=0,
        digest_status=DigestStatus.EMPTY_SKIPPED.value,
    )

