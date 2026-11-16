"""
Celery application instance for the Team Engagement platform.

Architecture:
  - Broker  : RabbitMQ (AMQP) — durable, at-least-once message delivery.
              If a worker crashes mid-task, the message is re-queued automatically
              because task_acks_late=True means the ACK is sent only after the
              task body completes successfully.
  - Backend : Redis db/1 — stores temporary task execution results so the API
              can poll job status without hitting PostgreSQL for every request.
              Business-critical state is ALWAYS stored in the PipelineRun table;
              Redis is a convenience cache only.

The celery_app object is imported by:
  - app/tasks/*.py  (task definitions via @shared_task)
  - app/routers/admin.py  (task.delay() calls)
  - app/jobs/daily_scan.py  (cron entry point)
  - Worker startup command: celery -A app.celery_app.celery_app worker
"""
from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "team_engagement",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.pipeline_tasks",
        "app.tasks.email_tasks",
        "app.tasks.hrms_tasks",
    ],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone — keep everything in business timezone for consistent log timestamps.
    timezone=settings.BUSINESS_TIMEZONE,
    enable_utc=True,

    # Reliability
    # task_acks_late: message is ACKed from RabbitMQ only AFTER the task body
    # returns successfully. If the worker dies mid-execution, RabbitMQ re-queues
    # the message and another worker will pick it up.
    task_acks_late=True,

    # worker_prefetch_multiplier=1: each worker fetches one task at a time.
    # This prevents a slow SMTP task from blocking a fast scanner task on the same worker.
    worker_prefetch_multiplier=1,

    # task_track_started: the task transitions to STARTED state before execution begins.
    # This lets the job-status API surface a "running" state to the dashboard.
    task_track_started=True,

    # Result TTL: keep task results in Redis for 24 hours, then auto-expire.
    # Long-term job history lives in the PipelineRun PostgreSQL table.
    result_expires=86400,
)
