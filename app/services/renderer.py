"""
Template rendering: static HTML + Jinja2 placeholders only.
No LLM, no free-text generation — every field comes straight from HRMS data
so output is 100% predictable and reviewable before it's ever seeded.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, StrictUndefined, TemplateError, select_autoescape
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmployeeProfile, EventLog, EventStatus, EventTemplate, EventType

settings = get_settings()
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# StrictUndefined makes a missing placeholder raise loudly instead of rendering
# the literal string "{{ name }}" into a live email.
_env = Environment(
    autoescape=select_autoescape(["html"]),
    undefined=StrictUndefined,
)


class RenderError(Exception):
    pass


def select_variant(event_type: EventType, years: int | None) -> str:
    """Pure lookup — no generation. Determines which pre-built template to use."""
    if event_type == EventType.BIRTHDAY:
        return "default"
    # work anniversary milestone tiers
    if years is not None and years >= 10:
        return "anniversary_10yr"
    if years is not None and years >= 5:
        return "anniversary_5yr"
    return "anniversary_default"


def get_active_template(
    db: Session,
    event_type: EventType,
    variant_key: str,
    organization_id: str | None = None,
) -> EventTemplate:
    """
    Look up the active template for (organization_id, event_type, variant_key).
    Falls back to the generic 'default'/'anniversary_default' variant if a
    milestone-specific template has been deactivated.
    """
    q = db.query(EventTemplate).filter(
        EventTemplate.event_type == event_type,
        EventTemplate.variant_key == variant_key,
        EventTemplate.is_active.is_(True),
    )
    if organization_id:
        q = q.filter(EventTemplate.organization_id == organization_id)

    tmpl = q.first()
    if tmpl:
        return tmpl

    fallback_key = "default" if event_type == EventType.BIRTHDAY else "anniversary_default"
    if variant_key != fallback_key:
        q_fallback = db.query(EventTemplate).filter(
            EventTemplate.event_type == event_type,
            EventTemplate.variant_key == fallback_key,
            EventTemplate.is_active.is_(True),
        )
        if organization_id:
            q_fallback = q_fallback.filter(EventTemplate.organization_id == organization_id)

        tmpl = q_fallback.first()
        if tmpl:
            return tmpl

    raise RenderError(f"No active template found for {event_type}/{variant_key} (or its fallback)")


def build_context(
    employee: EmployeeProfile,
    years: int | None,
    company_name: str | None = None,
    company_logo_url: str | None = None,
) -> dict:
    org_name = company_name or (employee.organization.name if employee.organization else None) or settings.COMPANY_NAME
    org_logo = company_logo_url or (employee.organization.company_logo_url if employee.organization else None) or settings.COMPANY_LOGO_URL

    return {
        "name": employee.preferred_name or employee.full_name,
        "photo_url": employee.photo_url or settings.DEFAULT_AVATAR_URL,
        "department": employee.department,
        "years": years,
        "company_name": org_name,
        "company_logo_url": org_logo,
    }


def render_event(db: Session, event: EventLog) -> EventLog:
    """
    Renders one EventLog row in place: resolves the template, substitutes
    placeholders, and transitions status pending -> rendered (or -> failed).
    """
    employee = event.employee or db.get(EmployeeProfile, event.employee_id)
    if employee is None:
        event.status = EventStatus.FAILED
        event.error_detail = f"Employee {event.employee_id} not found"
        return event

    variant_key = select_variant(event.event_type, event.years)

    try:
        template = get_active_template(
            db, event.event_type, variant_key, organization_id=event.organization_id
        )
        context = build_context(employee, event.years)
        subject_tpl = _env.from_string(template.subject_line)
        body_tpl = _env.from_string(template.html_body)

        event.rendered_subject = subject_tpl.render(**context)
        event.rendered_html = body_tpl.render(**context)
        event.template_id = template.id
        event.status = EventStatus.RENDERED
        event.error_detail = None
    except (RenderError, TemplateError) as exc:
        event.status = EventStatus.FAILED
        event.error_detail = f"Render failure: {exc}"

    return event



def load_seed_template_file(filename: str) -> str:
    path = TEMPLATES_DIR / filename
    return path.read_text(encoding="utf-8")
