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

    has_custom = bool(getattr(employee, "has_custom_photo", False) and employee.photo_url)
    return {
        "name": employee.preferred_name or employee.full_name,
        "photo_url": employee.photo_url if (employee.photo_url and has_custom) else (employee.photo_url or settings.DEFAULT_AVATAR_URL),
        "has_custom_photo": has_custom,
        "department": employee.department,
        "years": years,
        "company_name": org_name,
        "company_logo_url": org_logo,
    }


def resolve_template_for_event(
    db: Session,
    employee: EmployeeProfile,
    event_type: EventType,
    years: int | None,
    organization_id: str | None,
) -> EventTemplate:
    """
    Resolves the exact template to render:
    1. If employee has a specific template assigned for this event type and it is active, use it!
    2. If no specific template is assigned, resolve the organization's active default template
       (or milestone-tier variant if applicable for anniversaries).
    3. Fall back to any active default template for that event type.
    4. Fall back to any active template of that event type in the organization.
    """
    # 1. Member-specific assigned template
    assigned_template_id = None
    if event_type == EventType.BIRTHDAY and employee.birthday_template_id:
        assigned_template_id = employee.birthday_template_id
    elif event_type == EventType.WORK_ANNIVERSARY and employee.anniversary_template_id:
        assigned_template_id = employee.anniversary_template_id

    if assigned_template_id:
        tmpl_q = db.query(EventTemplate).filter(
            EventTemplate.id == assigned_template_id,
            EventTemplate.is_active.is_(True),
        )
        if organization_id:
            tmpl_q = tmpl_q.filter(EventTemplate.organization_id == organization_id)
        found = tmpl_q.first()
        if found:
            return found

    # 2. Anniversary milestone-tier check (e.g. 5yr, 10yr) if configured
    if event_type == EventType.WORK_ANNIVERSARY:
        variant_key = select_variant(event_type, years)
        if variant_key in ("anniversary_5yr", "anniversary_10yr"):
            milestone_q = db.query(EventTemplate).filter(
                EventTemplate.event_type == event_type,
                EventTemplate.variant_key == variant_key,
                EventTemplate.is_active.is_(True),
            )
            if organization_id:
                milestone_q = milestone_q.filter(EventTemplate.organization_id == organization_id)
            milestone_tmpl = milestone_q.first()
            if milestone_tmpl:
                return milestone_tmpl

    # 3. Organization Default template (is_default == True)
    default_q = db.query(EventTemplate).filter(
        EventTemplate.event_type == event_type,
        EventTemplate.is_default.is_(True),
        EventTemplate.is_active.is_(True),
    )
    if organization_id:
        default_q = default_q.filter(EventTemplate.organization_id == organization_id)
    default_tmpl = default_q.first()
    if default_tmpl:
        return default_tmpl

    # 4. Fall back by variant_key ("default" or "anniversary_default")
    fallback_key = "default" if event_type == EventType.BIRTHDAY else "anniversary_default"
    fallback_q = db.query(EventTemplate).filter(
        EventTemplate.event_type == event_type,
        EventTemplate.variant_key == fallback_key,
        EventTemplate.is_active.is_(True),
    )
    if organization_id:
        fallback_q = fallback_q.filter(EventTemplate.organization_id == organization_id)
    fallback_tmpl = fallback_q.first()
    if fallback_tmpl:
        return fallback_tmpl

    # 5. Fall back to ANY active template of that event type
    any_q = db.query(EventTemplate).filter(
        EventTemplate.event_type == event_type,
        EventTemplate.is_active.is_(True),
    )
    if organization_id:
        any_q = any_q.filter(EventTemplate.organization_id == organization_id)
    any_tmpl = any_q.first()
    if any_tmpl:
        return any_tmpl

    raise RenderError(f"No active template found for {event_type} in organization {organization_id}")


def preview_template_render(
    subject_line: str,
    html_body: str,
    event_type: EventType,
    custom_context: dict | None = None,
) -> tuple[str, str]:
    """Renders a template subject and HTML body with sample preview context."""
    default_context = {
        "name": "Alex Morgan",
        "preferred_name": "Alex",
        "photo_url": settings.DEFAULT_AVATAR_URL,
        "department": "Product Engineering",
        "years": 5 if event_type == EventType.WORK_ANNIVERSARY else None,
        "company_name": settings.COMPANY_NAME,
        "company_logo_url": settings.COMPANY_LOGO_URL,
    }
    if custom_context:
        default_context.update(custom_context)

    try:
        subject_tpl = _env.from_string(subject_line)
        body_tpl = _env.from_string(html_body)
        rendered_subject = subject_tpl.render(**default_context)
        rendered_html = body_tpl.render(**default_context)
        return rendered_subject, rendered_html
    except Exception as exc:
        raise RenderError(f"Template preview render failed: {exc}")


def render_event(db: Session, event: EventLog) -> EventLog:
    """
    Renders one EventLog row in place: resolves member-specific template or default,
    substitutes placeholders, and transitions status pending -> rendered (or -> failed).
    """
    employee = event.employee or db.get(EmployeeProfile, event.employee_id)
    if employee is None:
        event.status = EventStatus.FAILED
        event.error_detail = f"Employee {event.employee_id} not found"
        return event

    try:
        template = resolve_template_for_event(
            db,
            employee=employee,
            event_type=event.event_type,
            years=event.years,
            organization_id=event.organization_id,
        )
        context = build_context(employee, event.years)
        subject_tpl = _env.from_string(template.subject_line)
        body_tpl = _env.from_string(template.html_body)

        event.rendered_subject = subject_tpl.render(**context)
        event.rendered_html = body_tpl.render(**context)
        event.template_id = template.id
        event.used_custom_photo = context.get("has_custom_photo", False)
        event.status = EventStatus.RENDERED
        event.error_detail = None
    except (RenderError, TemplateError) as exc:
        event.status = EventStatus.FAILED
        event.error_detail = f"Render failure: {exc}"

    return event



def load_seed_template_file(filename: str) -> str:
    path = TEMPLATES_DIR / filename
    return path.read_text(encoding="utf-8")
