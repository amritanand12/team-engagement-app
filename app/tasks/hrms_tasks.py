"""
HRMS synchronization Celery task.

Runs the existing sync_employees() service function as a background task so the
POST /admin/hrms-sync/trigger endpoint returns 202 immediately instead of
blocking the API for the duration of the HTTP call to the HRMS provider.
"""
from __future__ import annotations

import logging

from celery import shared_task

from app.database import session_scope
from app.models import EmployeeProfile
from app.repositories.job_repository import mark_completed, mark_failed, mark_running
from app.services.hrms_sync import sync_employees

logger = logging.getLogger("engagement.tasks.hrms")


@shared_task(
    bind=True,
    name="app.tasks.hrms_tasks.sync_hrms_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 3},
)
def sync_hrms_task(self, org_id: str) -> dict:
    """
    Pull the latest employee roster from the HRMS provider for one organization
    and upsert records into the local EmployeeProfile table.

    Args:
        org_id: The organization to sync.

    Returns a dict summarising how many records were created / updated.
    """
    task_id = self.request.id
    logger.info("HRMS sync task starting: org_id=%s task_id=%s", org_id, task_id)

    with session_scope() as db:
        mark_running(db, task_id)

        try:
            created, updated = sync_employees(db)

            # Refresh cached employee count on org record
            from app.models import Organization
            org = db.get(Organization, org_id)
            if org:
                org.cached_employee_count = (
                    db.query(EmployeeProfile)
                    .filter(EmployeeProfile.organization_id == org_id)
                    .count()
                )
                db.commit()

            summary = {
                "org_id": org_id,
                "created": created,
                "updated": updated,
                "message": f"HRMS sync completed: {created} created, {updated} updated",
            }
            mark_completed(db, task_id, summary)
            logger.info("HRMS sync completed: %s", summary)
            return summary

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception("HRMS sync task failed: org_id=%s", org_id)
            mark_failed(db, task_id, error_msg)
            raise  # triggers autoretry
