"""
Cron scheduling via APScheduler, pinned to the business timezone.

In production you may prefer to trigger `run_daily_pipeline` from an external
scheduler instead (Celery beat, n8n Cron node hitting POST /admin/scan/trigger,
Kubernetes CronJob) rather than an in-process APScheduler — this in-process
scheduler is fine for a single-instance deployment but doesn't coordinate
across multiple replicas. If you run >1 app instance, move scheduling out of
the process and rely on the admin endpoint + a distributed lock (Redis) instead.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import session_scope
from app.services.pipeline import run_daily_pipeline

logger = logging.getLogger("engagement.scheduler")
settings = get_settings()

_scheduler: BackgroundScheduler | None = None


def _scheduled_job() -> None:
    with session_scope() as db:
        try:
            result = run_daily_pipeline(db)
            logger.info("Scheduled pipeline run finished: %s", result)
        except Exception:
            logger.exception("Scheduled pipeline run failed")


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.ENABLE_SCHEDULER:
        logger.info("Scheduler disabled via ENABLE_SCHEDULER=false")
        return None

    _scheduler = BackgroundScheduler(timezone=settings.BUSINESS_TIMEZONE)
    _scheduler.add_job(
        _scheduled_job,
        CronTrigger(hour=settings.DAILY_SCAN_HOUR, minute=settings.DAILY_SCAN_MINUTE),
        id="daily_engagement_scan",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: daily run at %02d:%02d %s",
        settings.DAILY_SCAN_HOUR, settings.DAILY_SCAN_MINUTE, settings.BUSINESS_TIMEZONE,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
