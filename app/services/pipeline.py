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
import os
from pathlib import Path

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
        attachment_path = None
        html_to_send = event.rendered_html or ""
        if event.used_custom_photo and employee.photo_url:
            clean_rel = employee.photo_url.lstrip("/").replace("/", os.sep)
            if os.path.isfile(clean_rel):
                attachment_path = clean_rel
            elif os.path.isfile(employee.photo_url):
                attachment_path = employee.photo_url

            if attachment_path:
                # Replace local URL with cid:celebration_photo so email clients display it directly in the card
                html_to_send = html_to_send.replace(employee.photo_url, "cid:celebration_photo")
                html_to_send = html_to_send.replace(f"/{employee.photo_url.lstrip('/')}", "cid:celebration_photo")

        success, error = send_with_retry(
            mailer,
            employee.email,
            event.rendered_subject,
            html_to_send,
            attachment_path=attachment_path,
        )
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

    from contextlib import nullcontext
    from app.database import tenant_session_scope

    is_dedicated = bool(
        org
        and getattr(org, "is_db_configured", False)
        and getattr(org, "db_host", None)
        and getattr(org, "db_name", None)
        and not getattr(org, "is_demo", False)
    )
    ctx = tenant_session_scope(org) if is_dedicated else nullcontext(db)

    with ctx as tdb:
        detected, batch_id = scanner.run_scan(
            tdb, scan_date, organization_id=organization_id, leap_day_policy=leap_policy
        )
        tdb.commit()

        _render_pending(tdb, batch_id, organization_id=organization_id)
        tdb.commit()

        _send_individual_emails(tdb, batch_id, mailer, organization_id=organization_id)
        tdb.commit()

        digest_status = _send_digest(tdb, batch_id, scan_date, mailer, org=org)
        tdb.commit()

        counts = {
            EventStatus.SENT: 0,
            EventStatus.FAILED: 0,
            EventStatus.SKIPPED: 0,
            EventStatus.RENDERED: 0,
        }
        rows = (
            tdb.query(EventLog.status)
            .filter(EventLog.batch_id == batch_id, EventLog.organization_id == organization_id)
            .all()
        )
        for (status,) in rows:
            counts[status] = counts.get(status, 0) + 1

        # Cache high-level counts in platform db
        try:
            total_emp = tdb.query(EmployeeProfile).filter(EmployeeProfile.organization_id == organization_id).count()
            total_ev = tdb.query(EventLog).filter(EventLog.organization_id == organization_id).count()
            if org:
                org.cached_employee_count = total_emp
                org.cached_event_count = total_ev
                db.commit()
        except Exception as cache_exc:
            logger.warning("Could not update cached counts for org %s: %s", organization_id, cache_exc)

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

