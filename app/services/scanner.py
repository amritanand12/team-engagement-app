"""
Daily scan: finds employees whose birthday or work-anniversary falls on the
given date, and idempotently inserts pending EventLog rows for them.

Idempotency comes from the UNIQUE(employee_id, event_type, event_date)
constraint on EventLog — re-running the scan for a date that was already
scanned is always safe and never creates duplicates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine
from app.models import EmployeeProfile, EventLog, EventStatus, EventType

settings = get_settings()


@dataclass
class DueEvent:
    employee_id: str
    organization_id: str
    event_type: EventType
    event_date: date
    years: int | None


def _years_between(start: date, today: date) -> int:
    years = today.year - start.year
    if (today.month, today.day) < (start.month, start.day):
        years -= 1
    return years


def _effective_birthday_month_day(dob: date, scan_year: int, leap_day_policy: str = "feb28") -> tuple[int, int] | None:
    """
    Resolves Feb-29 birthdays against leap_day_policy for non-leap scan years.
    Returns (month, day) to match against, or None if the event should not
    fire this year (policy == 'leap_only' and scan_year is not a leap year).
    """
    is_leap_scan_year = scan_year % 4 == 0 and (scan_year % 100 != 0 or scan_year % 400 == 0)

    if not (dob.month == 2 and dob.day == 29):
        return (dob.month, dob.day)

    if is_leap_scan_year:
        return (2, 29)

    policy = leap_day_policy or settings.LEAP_DAY_POLICY
    if policy == "feb28":
        return (2, 28)
    if policy == "mar1":
        return (3, 1)
    return None  # "leap_only" -> skip in non-leap years


def find_due_events(
    db: Session,
    scan_date: date,
    organization_id: str | None = None,
    leap_day_policy: str | None = None,
) -> list[DueEvent]:
    """Pure detection logic, scoped to organization if provided."""
    due: list[DueEvent] = []

    stmt = select(EmployeeProfile).where(EmployeeProfile.is_active.is_(True))
    if organization_id:
        stmt = stmt.where(EmployeeProfile.organization_id == organization_id)

    employees = db.execute(stmt).scalars().all()

    for emp in employees:
        policy = leap_day_policy or settings.LEAP_DAY_POLICY
        if emp.date_of_birth:
            md = _effective_birthday_month_day(emp.date_of_birth, scan_date.year, policy)
            if md == (scan_date.month, scan_date.day):
                due.append(DueEvent(emp.id, emp.organization_id, EventType.BIRTHDAY, scan_date, None))

        if emp.date_of_joining:
            doj = emp.date_of_joining
            # Exclude the literal day someone joined (0-year "anniversary").
            if (
                doj.month == scan_date.month
                and doj.day == scan_date.day
                and doj < scan_date
            ):
                years = _years_between(doj, scan_date)
                due.append(DueEvent(emp.id, emp.organization_id, EventType.WORK_ANNIVERSARY, scan_date, years))

    return due


def persist_due_events(db: Session, due_events: list[DueEvent], batch_id: str) -> int:
    """
    Idempotent upsert into event_log. Returns the number of NEW rows inserted.
    """
    if not due_events:
        return 0

    is_sqlite = engine.dialect.name == "sqlite"
    insert_fn = sqlite_insert if is_sqlite else pg_insert

    rows = [
        {
            "id": __import__("uuid").uuid4().hex,
            "organization_id": e.organization_id,
            "employee_id": e.employee_id,
            "event_type": e.event_type,
            "event_date": e.event_date,
            "years": e.years,
            "status": EventStatus.PENDING,
            "batch_id": batch_id,
        }
        for e in due_events
    ]

    stmt = insert_fn(EventLog).values(rows)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["organization_id", "employee_id", "event_type", "event_date"]
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount or 0


def run_scan(
    db: Session,
    scan_date: date,
    organization_id: str | None = None,
    leap_day_policy: str | None = None,
) -> tuple[int, str]:
    batch_id = scan_date.isoformat()
    due = find_due_events(db, scan_date, organization_id=organization_id, leap_day_policy=leap_day_policy)
    inserted = persist_due_events(db, due, batch_id)
    return inserted, batch_id

