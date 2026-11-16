"""
Daily scan entry point — called by the Render Cron Job at 6 AM IST (00:30 UTC).

This is a one-shot script: it enqueues a Celery task into RabbitMQ and exits.
The actual pipeline work is done asynchronously by the Celery worker process.

Render Cron Job configuration:
  Schedule : 30 0 * * *   (00:30 UTC = 06:00 IST)
  Command  : python -m app.jobs.daily_scan

Why a separate script instead of Celery Beat?
  Celery Beat requires its own always-on process. Using Render's managed Cron Job
  is cheaper (serverless, only runs for a few seconds) and simpler to monitor.
  The job just publishes a message to RabbitMQ and exits; the worker does the rest.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("engagement.jobs.daily_scan")


def main() -> None:
    from app.tasks.pipeline_tasks import run_pipeline_task
    from app.repositories.job_repository import create_job
    from app.database import session_scope

    logger.info("Daily scan cron job triggered at %s", datetime.utcnow().isoformat())

    # Create a PipelineRun QUEUED record before publishing, so the job is
    # visible in the dashboard even if the worker is temporarily overloaded.
    with session_scope() as db:
        # Publish task to RabbitMQ; Celery returns an AsyncResult with the task_id
        async_result = run_pipeline_task.delay(
            organization_id=None,     # run for all active orgs
            scan_date_iso=None,       # defaults to today in business timezone
        )
        task_id = async_result.id
        create_job(
            db,
            job_type="DAILY_SCAN",
            task_id=task_id,
            organization_id=None,
        )

    logger.info(
        "Daily scan task queued successfully: task_id=%s — worker will execute shortly",
        task_id,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
