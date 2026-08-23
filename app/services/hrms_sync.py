"""
Syncs employee_profile from HRMS. Decoupled from the daily scan so the scan
never depends on HRMS uptime/rate limits at 6am.

This is a stub adapter — swap `fetch_hrms_employees()` for your actual HRMS
API client (REST/SOAP/DB export, whatever your HRMS exposes). The rest of
the pipeline only depends on the local `employee_profile` table.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmployeeProfile

logger = logging.getLogger("engagement.hrms_sync")
settings = get_settings()


def fetch_hrms_employees() -> list[dict[str, Any]]:
    """
    Replace with a real HRMS API call. Expected shape per record:
    {
      "employee_code": str, "full_name": str, "preferred_name": str|None,
      "email": str, "photo_url": str|None,
      "date_of_birth": "YYYY-MM-DD"|None, "date_of_joining": "YYYY-MM-DD"|None,
      "department": str|None, "manager_employee_code": str|None,
      "team_channel_id": str|None, "is_active": bool
    }
    """
    if not settings.HRMS_API_TOKEN:
        logger.warning("HRMS_API_TOKEN not set — skipping live fetch (returning empty list)")
        return []

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{settings.HRMS_API_BASE_URL}/employees",
            headers={"Authorization": f"Bearer {settings.HRMS_API_TOKEN}"},
        )
        resp.raise_for_status()
        return resp.json()


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def sync_employees(db: Session, records: list[dict[str, Any]] | None = None) -> tuple[int, int]:
    """Upserts employee_profile rows by employee_code. Returns (created, updated)."""
    records = records if records is not None else fetch_hrms_employees()
    created, updated = 0, 0

    code_to_id: dict[str, str] = {
        row.employee_code: row.id for row in db.query(EmployeeProfile).all()
    }

    for rec in records:
        existing = db.query(EmployeeProfile).filter(
            EmployeeProfile.employee_code == rec["employee_code"]
        ).first()

        manager_id = None
        mgr_code = rec.get("manager_employee_code")
        if mgr_code:
            manager_id = code_to_id.get(mgr_code)

        payload = dict(
            full_name=rec["full_name"],
            preferred_name=rec.get("preferred_name"),
            email=rec["email"],
            photo_url=rec.get("photo_url"),
            date_of_birth=_parse_date(rec.get("date_of_birth")),
            date_of_joining=_parse_date(rec.get("date_of_joining")),
            department=rec.get("department"),
            manager_id=manager_id,
            team_channel_id=rec.get("team_channel_id"),
            is_active=rec.get("is_active", True),
            last_synced_at=datetime.utcnow(),
        )

        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            updated += 1
        else:
            emp = EmployeeProfile(employee_code=rec["employee_code"], **payload)
            db.add(emp)
            db.flush()
            code_to_id[rec["employee_code"]] = emp.id
            created += 1

    db.commit()
    logger.info("HRMS sync complete: %d created, %d updated", created, updated)
    return created, updated
