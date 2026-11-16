"""
Builds the single team/company-wide digest for a batch (day), merging
same-day events so a channel never receives N separate posts for N people —
and so an employee with two events that day (birthday + anniversary) shows
up once, in a combined section, rather than twice.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, StrictUndefined, select_autoescape
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmployeeProfile, EventLog, EventStatus, EventType

settings = get_settings()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(autoescape=select_autoescape(["html"]), undefined=StrictUndefined)


def _person_dict(employee: EmployeeProfile, years: int | None = None) -> dict:
    return {
        "name": employee.preferred_name or employee.full_name,
        "photo_url": employee.photo_url or settings.DEFAULT_AVATAR_URL,
        "department": employee.department,
        "years": years,
    }


def group_events_for_digest(events: list[EventLog]) -> dict:
    """
    Splits a flat list of same-day EventLog rows into:
      - combined_people: employees with BOTH a birthday and an anniversary today
      - birthdays: remaining birthday-only people
      - anniversaries: remaining anniversary-only people
    """
    by_employee: dict[str, list[EventLog]] = {}
    for e in events:
        by_employee.setdefault(e.employee_id, []).append(e)

    combined_people, birthdays, anniversaries = [], [], []

    for emp_id, emp_events in by_employee.items():
        types = {e.event_type for e in emp_events}
        employee = emp_events[0].employee
        if EventType.BIRTHDAY in types and EventType.WORK_ANNIVERSARY in types:
            anniv = next(e for e in emp_events if e.event_type == EventType.WORK_ANNIVERSARY)
            combined_people.append(_person_dict(employee, anniv.years))
        elif EventType.BIRTHDAY in types:
            birthdays.append(_person_dict(employee))
        else:
            anniv = next(e for e in emp_events if e.event_type == EventType.WORK_ANNIVERSARY)
            anniversaries.append(_person_dict(employee, anniv.years))

    return {
        "combined_people": combined_people,
        "birthdays": birthdays,
        "anniversaries": anniversaries,
    }


def render_digest(
    events: list[EventLog],
    batch_date: date,
    company_name: str | None = None,
    company_logo_url: str | None = None,
) -> str | None:
    """Returns rendered HTML, or None if there is nothing to send (empty digest)."""
    if not events:
        return None

    grouped = group_events_for_digest(events)
    template_src = (TEMPLATES_DIR / "digest.html").read_text(encoding="utf-8")
    template = _env.from_string(template_src)

    org_name = company_name or settings.COMPANY_NAME
    org_logo = company_logo_url or settings.COMPANY_LOGO_URL

    return template.render(
        display_date=batch_date.strftime("%B %d, %Y"),
        company_name=org_name,
        company_logo_url=org_logo,
        max_visible=settings.DIGEST_MAX_VISIBLE_PER_SECTION,
        **grouped,
    )


def get_renderable_events_for_batch(
    db: Session,
    batch_id: str,
    organization_id: str | None = None,
) -> list[EventLog]:
    """Events that were successfully rendered (or sent) for this batch — used for the digest."""
    q = db.query(EventLog).filter(
        EventLog.batch_id == batch_id,
        EventLog.status.in_([EventStatus.RENDERED, EventStatus.SENT]),
    )
    if organization_id:
        q = q.filter(EventLog.organization_id == organization_id)
    return q.all()

