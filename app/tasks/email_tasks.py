"""
Email resend Celery task.

Runs the resend flow for a single EventLog record as a background task.
This frees the API from waiting for SMTP and makes the POST /admin/events/{id}/resend
endpoint return 202 immediately.

Concurrency safety:
  The task checks EventLog.status == SENT before sending and uses a Redis lock
  keyed on the event_id so two concurrent resend attempts on the same event
  cannot both proceed past the guard.

  Flow:
    1. Acquire Redis lock for this event_id (TTL = 120 s)
    2. Re-fetch event inside a fresh DB session (avoid stale cache)
    3. Refuse if already SENT
    4. Render if HTML is missing
    5. Send via mailer
    6. Commit status update
    7. Release lock
"""
from __future__ import annotations

import logging
from datetime import datetime

from celery import shared_task

from app.database import session_scope
from app.models import EmployeeProfile, EventLog, EventStatus
from app.repositories.job_repository import mark_completed, mark_failed, mark_running
from app.services.cache import acquire_lock, release_lock
from app.services.mailer import get_mailer
from app.services.renderer import render_event
from app.services.mailer import send_with_retry

logger = logging.getLogger("engagement.tasks.email")

_RESEND_LOCK_TTL = 120  # seconds


@shared_task(
    bind=True,
    name="app.tasks.email_tasks.resend_event_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_kwargs={"max_retries": 3},
)
def resend_event_task(self, event_id: str, org_id: str) -> dict:
    """
    Resend a single celebration email in the background.

    Args:
        event_id: Primary key of the EventLog row to resend.
        org_id:   Organization ID (used to get correct mailer config).

    Returns a dict describing the outcome.
    """
    task_id = self.request.id
    lock_key = f"resend_lock:{event_id}"
    lock_token = task_id  # unique per attempt

    logger.info("Resend task starting: event_id=%s task_id=%s", event_id, task_id)

    with session_scope() as db:
        mark_running(db, task_id)

        # Acquire distributed lock — prevents two admins queueing simultaneous resends
        if not acquire_lock(lock_key, lock_token, ttl=_RESEND_LOCK_TTL):
            msg = f"Event {event_id} is already being processed by another worker"
            logger.warning(msg)
            mark_completed(db, task_id, {"skipped": True, "reason": msg})
            return {"event_id": event_id, "status": "skipped", "message": msg}

        try:
            from app.models import Organization
            org = db.get(Organization, org_id)

            # Always re-fetch inside the task — avoids stale state from the API process
            event = db.query(EventLog).filter(
                EventLog.id == event_id,
                EventLog.organization_id == org_id,
            ).first()

            if not event:
                msg = f"Event {event_id} not found"
                mark_failed(db, task_id, msg)
                return {"event_id": event_id, "status": "not_found"}

            if event.status == EventStatus.SENT:
                msg = "Already sent — refusing to resend"
                mark_completed(db, task_id, {"skipped": True, "reason": msg})
                return {"event_id": event_id, "status": "already_sent"}

            # Render if HTML is missing
            if not event.rendered_html:
                render_event(db, event)
                db.flush()
                if event.status == EventStatus.FAILED:
                    msg = event.error_detail or "Render failed"
                    mark_failed(db, task_id, msg)
                    return {"event_id": event_id, "status": "render_failed", "detail": msg}

            employee = event.employee or db.get(EmployeeProfile, event.employee_id)
            if not employee or not employee.email:
                event.status = EventStatus.FAILED
                event.error_detail = "Employee has no email address"
                db.commit()
                mark_failed(db, task_id, event.error_detail)
                return {"event_id": event_id, "status": "failed", "detail": event.error_detail}

            mailer = get_mailer(org)
            event.attempt_count += 1
            success, error = send_with_retry(
                mailer, employee.email, event.rendered_subject, event.rendered_html
            )

            if success:
                event.status = EventStatus.SENT
                event.sent_at = datetime.utcnow()
                event.error_detail = None
                db.commit()
                summary = {"event_id": event_id, "status": "sent"}
                mark_completed(db, task_id, summary)
                logger.info("Resend successful: event_id=%s", event_id)
                return summary
            else:
                event.status = EventStatus.FAILED
                event.error_detail = error
                db.commit()
                mark_failed(db, task_id, error or "Send failed")
                return {"event_id": event_id, "status": "failed", "detail": error}

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception("Resend task failed: event_id=%s", event_id)
            mark_failed(db, task_id, error_msg)
            raise  # triggers autoretry

        finally:
            release_lock(lock_key, lock_token)
