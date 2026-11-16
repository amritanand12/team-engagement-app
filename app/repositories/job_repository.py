"""
PipelineRun repository — pure database operations, no business logic.

Each public function accepts a SQLAlchemy Session and operates on PipelineRun rows.
Keeping these out of the router and task layers makes them independently testable.

Functions:
  create_job()      — Insert a new QUEUED PipelineRun row
  get_job()         — Fetch by primary key
  get_job_by_task_id() — Fetch by Celery task_id
  list_jobs()       — Paginated history
  mark_running()    — QUEUED → RUNNING (called at task start)
  mark_completed()  — RUNNING → COMPLETED (called after successful execution)
  mark_failed()     — RUNNING → FAILED (called on exception)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import JobStatus, PipelineRun

logger = logging.getLogger("engagement.repositories.job")


def create_job(
    db: Session,
    *,
    job_type: str,
    task_id: str,
    organization_id: str | None = None,
    scan_date_iso: str | None = None,
) -> PipelineRun:
    """
    Create a new PipelineRun row with status QUEUED.

    Call this BEFORE publishing the Celery task so the job is visible in the
    dashboard immediately upon submission, even before the worker picks it up.
    """
    from datetime import date as date_type
    run = PipelineRun(
        task_id=task_id,
        job_type=job_type,
        organization_id=organization_id,
        status=JobStatus.QUEUED,
        scan_date=(
            date_type.fromisoformat(scan_date_iso) if scan_date_iso else None
        ),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info("Job created: id=%s task_id=%s type=%s", run.id, task_id, job_type)
    return run


def get_job(db: Session, job_id: str) -> PipelineRun | None:
    """Fetch a PipelineRun by its primary key UUID."""
    return db.get(PipelineRun, job_id)


def get_job_by_task_id(db: Session, task_id: str) -> PipelineRun | None:
    """Fetch a PipelineRun by its Celery task_id."""
    return db.query(PipelineRun).filter(PipelineRun.task_id == task_id).first()


def list_jobs(
    db: Session,
    *,
    organization_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[PipelineRun], int]:
    """
    Return a paginated list of PipelineRun rows, most-recent first.

    Returns (items, total_count).
    """
    q = db.query(PipelineRun)
    if organization_id:
        q = q.filter(PipelineRun.organization_id == organization_id)
    total = q.count()
    items = q.order_by(PipelineRun.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def mark_running(db: Session, task_id: str) -> None:
    """
    Transition a PipelineRun from QUEUED → RUNNING.
    Called at the very start of each Celery task body.
    Safe to call even if the row doesn't exist yet (no-op in that case).
    """
    run = get_job_by_task_id(db, task_id)
    if run:
        run.status = JobStatus.RUNNING
        run.started_at = datetime.utcnow()
        db.commit()


def mark_completed(db: Session, task_id: str, result: dict) -> None:
    """
    Transition a PipelineRun to COMPLETED and persist the result summary.
    Called after a task body returns successfully.
    """
    run = get_job_by_task_id(db, task_id)
    if run:
        run.status = JobStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        run.result_json = json.dumps(result, default=str)
        db.commit()


def mark_failed(db: Session, task_id: str, error: str) -> None:
    """
    Transition a PipelineRun to FAILED and store the error message.
    Called when an exception escapes the task body.
    """
    run = get_job_by_task_id(db, task_id)
    if run:
        run.status = JobStatus.FAILED
        run.completed_at = datetime.utcnow()
        run.error_message = error[:2000]  # guard against very long tracebacks
        db.commit()
