"""
Pipeline Celery task.

This wraps the existing run_tenant_pipeline() / run_daily_pipeline() service
functions as an asynchronous, retryable Celery task.

Key design decisions:
  - bind=True: gives `self` access so we can call self.retry() on recoverable errors.
  - autoretry_for=(Exception,): unexpected exceptions (network blip, DB timeout) are
    automatically retried up to max_retries=3 with exponential backoff.
  - Per-email SMTP failures are recorded as EventLog.status=FAILED by the pipeline
    internals and are NOT raised as exceptions, so Celery only retries on truly
    unexpected errors — not on "user has no email address" type failures.
  - The PipelineRun row is updated throughout execution so the job-status API
    always reflects the current state.

IMPORTANT — at-least-once delivery caveat:
  With task_acks_late=True, if a worker sends an email and then crashes before
  committing SENT status, a retry will re-attempt that send. The existing database
  UNIQUE(org, employee, event_type, event_date) constraint plus the SENT-exclusion
  guard in the mailer protect against most duplicates, but SMTP itself provides no
  built-in idempotency. Document this honestly in interviews.
"""
from __future__ import annotations

import logging
from datetime import date

from celery import shared_task

from app.database import session_scope
from app.repositories.job_repository import (
    get_job_by_task_id,
    mark_completed,
    mark_failed,
    mark_running,
)
from app.services.pipeline import run_daily_pipeline, run_tenant_pipeline

logger = logging.getLogger("engagement.tasks.pipeline")


@shared_task(
    bind=True,
    name="app.tasks.pipeline_tasks.run_pipeline_task",
    autoretry_for=(Exception,),
    retry_backoff=True,          # 2s, 4s, 8s … exponential
    retry_backoff_max=300,       # cap at 5 minutes
    retry_kwargs={"max_retries": 3},
    # Do not auto-retry on these — they are business-logic failures, not infra errors:
    dont_autoretry_for=(),
)
def run_pipeline_task(
    self,
    organization_id: str | None = None,
    scan_date_iso: str | None = None,
) -> dict:
    """
    Run the full scan → render → send → digest pipeline for one or all tenants.

    Args:
        organization_id: If provided, runs only for this tenant.
                         If None, runs for all active organizations.
        scan_date_iso:   ISO date string (YYYY-MM-DD). Defaults to today.

    Returns a dict with pipeline summary so the result can be stored in Redis.
    """
    task_id = self.request.id
    parsed_date = date.fromisoformat(scan_date_iso) if scan_date_iso else None

    logger.info(
        "Pipeline task starting: task_id=%s org=%s date=%s",
        task_id, organization_id or "ALL", scan_date_iso or "today",
    )

    with session_scope() as db:
        # Update PipelineRun to RUNNING so dashboard can show live status
        mark_running(db, task_id)

        try:
            if organization_id:
                result = run_tenant_pipeline(db, organization_id, scan_date=parsed_date)
            else:
                result = run_daily_pipeline(db, scan_date=parsed_date)

            summary = {
                "batch_id": result.batch_id,
                "detected": result.detected,
                "rendered": result.rendered,
                "sent": result.sent,
                "failed": result.failed,
                "skipped": result.skipped,
                "digest_status": result.digest_status,
            }

            mark_completed(db, task_id, summary)
            logger.info("Pipeline task completed: %s", summary)
            return summary

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception("Pipeline task failed: task_id=%s", task_id)
            mark_failed(db, task_id, error_msg)
            raise  # re-raise so Celery triggers autoretry


@shared_task(
    bind=True,
    name="app.tasks.pipeline_tasks.run_all_orgs_pipeline_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 3},
)
def run_all_orgs_pipeline_task(self, scan_date_iso: str | None = None) -> dict:
    """
    Daily cron entry point: runs the pipeline for every active organization.
    Called by app/jobs/daily_scan.py via the Render Cron Job at 6 AM IST.
    """
    return run_pipeline_task(
        self=self,
        organization_id=None,
        scan_date_iso=scan_date_iso,
    )
