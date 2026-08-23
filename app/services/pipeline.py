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
from app.models import DigestLog, DigestStatus, EmployeeProfile, EventLog, EventStatus
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


def _render_pending(db: Session, batch_id: str) -> None:
    """
    Renders anything not yet rendered: fresh PENDING rows, plus any row that
    previously FAILED at the rendering stage (no rendered_html yet) — so a
    transient issue (e.g. a template briefly deactivated) self-heals on the
    next scheduled/manual run without needing an explicit admin resend.
    Rows that already have rendered_html (i.e. failed at the SEND stage) are
    left alone here; retrying those is _send_individual_emails's job.
    """
    candidates = db.query(EventLog).filter(
        EventLog.batch_id == batch_id,
        EventLog.status.in_([EventStatus.PENDING, EventStatus.FAILED]),
        EventLog.rendered_html.is_(None),
    ).all()
    for event in candidates:
        render_event(db, event)
    db.flush()


def _send_individual_emails(db: Session, batch_id: str, mailer: BaseMailer) -> None:
    """
    Sends anything rendered-but-not-sent: fresh RENDERED rows, plus rows that
    previously FAILED at the send stage (rendered_html already present) — so a
    provider outage self-heals on the next pipeline run instead of silently
    leaving people un-notified until someone remembers to hit the resend endpoint.
    Rows already SENT are never touched, guaranteeing no duplicate emails.
    """
    rendered = db.query(EventLog).filter(
        EventLog.batch_id == batch_id,
        EventLog.status.in_([EventStatus.RENDERED, EventStatus.FAILED]),
        EventLog.rendered_html.isnot(None),
    ).all()

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


def _send_digest(db: Session, batch_id: str, batch_date: date, mailer: BaseMailer) -> str:
    events = digest_service.get_renderable_events_for_batch(db, batch_id)

    existing = db.query(DigestLog).filter(DigestLog.batch_id == batch_id).first()
    if existing and existing.status == DigestStatus.SENT:
        # Already sent for this batch — never double-post the team digest.
        return existing.status.value

    if not events:
        log = existing or DigestLog(batch_id=batch_id, channel_id=settings.DEFAULT_DIGEST_CHANNEL_ID)
        log.status = DigestStatus.EMPTY_SKIPPED
        log.event_count = 0
        if not existing:
            db.add(log)
        db.flush()
        return log.status.value

    html = digest_service.render_digest(events, batch_date)
    channel_id = settings.DEFAULT_DIGEST_CHANNEL_ID

    log = existing or DigestLog(batch_id=batch_id, channel_id=channel_id)
    log.rendered_html = html
    log.event_count = len(events)

    success, error = send_with_retry(
        mailer, channel_id, f"Celebrations today at {settings.COMPANY_NAME}", html
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


def run_daily_pipeline(db: Session, scan_date: date | None = None, mailer: BaseMailer | None = None) -> PipelineResult:
    scan_date = scan_date or date.today()
    mailer = mailer or get_mailer()

    detected, batch_id = scanner.run_scan(db, scan_date)
    db.commit()

    _render_pending(db, batch_id)
    db.commit()

    _send_individual_emails(db, batch_id, mailer)
    db.commit()

    digest_status = _send_digest(db, batch_id, scan_date, mailer)
    db.commit()

    counts = {
        EventStatus.SENT: 0,
        EventStatus.FAILED: 0,
        EventStatus.SKIPPED: 0,
        EventStatus.RENDERED: 0,
    }
    rows = db.query(EventLog.status).filter(EventLog.batch_id == batch_id).all()
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
    logger.info("Pipeline complete for batch %s: %s", batch_id, result)
    return result
