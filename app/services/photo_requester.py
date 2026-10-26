"""
Photo Request Service.
Orchestrates advance photo requests for upcoming birthdays and work anniversaries.
Allows employees to submit a photo of their choice via Google Form or built-in portal.
"""
from __future__ import annotations

import logging
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, StrictUndefined, select_autoescape
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmployeeProfile, EventType, Organization
from app.services.mailer import get_mailer, send_with_retry
from app.services.scanner import _effective_birthday_month_day, _years_between

logger = logging.getLogger("engagement.photo_requester")
settings = get_settings()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    autoescape=select_autoescape(["html"]),
    undefined=StrictUndefined,
)


def ensure_photo_token(employee: EmployeeProfile, refresh: bool = False) -> str:
    """Ensures the employee has a secure unique token for the upload portal."""
    if refresh or not employee.photo_upload_token:
        employee.photo_upload_token = secrets.token_urlsafe(24)
    return employee.photo_upload_token


def get_photo_submission_link(employee: EmployeeProfile, org: Organization) -> str:
    """
    Returns the URL for the employee to submit their photo.
    Prioritizes the organization's custom Google Form URL if configured,
    otherwise points to the built-in upload portal.
    """
    if org.google_form_url and org.google_form_url.strip():
        return org.google_form_url.strip()

    token = ensure_photo_token(employee)
    base_url = settings.APP_BASE_URL.rstrip("/")
    return f"{base_url}/upload-photo?token={token}"


def render_photo_request_email(
    employee: EmployeeProfile,
    org: Organization,
    event_label: str,
    celebration_date: date,
) -> tuple[str, str]:
    """Renders the subject and HTML body for the photo request invitation email."""
    template_path = TEMPLATES_DIR / "photo_request.html"
    template_content = template_path.read_text(encoding="utf-8")

    upload_link = get_photo_submission_link(employee, org)
    company_name = org.name or settings.COMPANY_NAME
    company_logo = org.company_logo_url or settings.COMPANY_LOGO_URL

    context = {
        "name": employee.preferred_name or employee.full_name,
        "event_label": event_label,
        "celebration_date": celebration_date.strftime("%B %d, %Y"),
        "upload_link": upload_link,
        "company_name": company_name,
        "company_logo_url": company_logo,
    }

    subject = f"📸 Share your photo for your upcoming {event_label} at {company_name}!"
    tpl = _jinja_env.from_string(template_content)
    html_body = tpl.render(**context)

    return subject, html_body


def send_single_photo_request(
    db: Session,
    employee_id: str,
    organization_id: str | None = None,
    force: bool = False,
    org: Organization | None = None,
) -> tuple[bool, str]:
    """
    Manually triggers a photo request email to an employee.
    Returns (success, message).
    """
    q = db.query(EmployeeProfile).filter(EmployeeProfile.id == employee_id)
    if organization_id:
        q = q.filter(EmployeeProfile.organization_id == organization_id)
    employee = q.first()

    if not employee:
        return False, "Employee not found"
    if not employee.email:
        return False, "Employee has no email address"

    if not org or not getattr(org, "smtp_host", None):
        org_id_to_fetch = organization_id or (employee.organization_id if employee else None)
        if org_id_to_fetch:
            from app.database import SessionLocal
            with SessionLocal() as platform_db:
                org = platform_db.get(Organization, org_id_to_fetch)

    if not org:
        org = employee.organization

    # Determine next celebration event
    today = date.today()
    event_label = "Celebration"
    target_celebration_date = today + timedelta(days=7)

    if employee.date_of_birth:
        event_label = "Birthday"
        target_celebration_date = date(today.year, employee.date_of_birth.month, employee.date_of_birth.day)
        if target_celebration_date < today:
            target_celebration_date = date(today.year + 1, employee.date_of_birth.month, employee.date_of_birth.day)
    elif employee.date_of_joining:
        event_label = "Work Anniversary"
        target_celebration_date = date(today.year, employee.date_of_joining.month, employee.date_of_joining.day)
        if target_celebration_date < today:
            target_celebration_date = date(today.year + 1, employee.date_of_joining.month, employee.date_of_joining.day)

    # Ensure a fresh token and timestamp for the 7-day expiration window
    ensure_photo_token(employee, refresh=True)
    employee.photo_request_sent_at = datetime.utcnow()
    db.commit()

    subject, html_body = render_photo_request_email(employee, org, event_label, target_celebration_date)
    mailer = get_mailer(org)

    success, error = send_with_retry(mailer, employee.email, subject, html_body)
    if success:
        return True, f"Photo request email successfully sent to {employee.email}"
    else:
        return False, f"Failed to send email: {error}"


def scan_and_send_advance_photo_requests(
    db: Session,
    organization_id: str | None = None,
    scan_date: date | None = None,
) -> list[dict]:
    """
    Scans for employees with upcoming birthdays or anniversaries (N days in advance)
    and sends them a photo request email if not already sent recently.
    """
    base_date = scan_date or date.today()
    results: list[dict] = []

    org_q = db.query(Organization).filter(Organization.is_active.is_(True))
    if organization_id:
        org_q = org_q.filter(Organization.id == organization_id)
    orgs = org_q.all()

    from app.database import tenant_session_scope

    for org in orgs:
        if not org.photo_request_enabled:
            continue

        days_ahead = org.photo_request_days_ahead or 7
        target_event_date = base_date + timedelta(days=days_ahead)

        with tenant_session_scope(org) as tdb:
            employees = tdb.query(EmployeeProfile).filter(
                EmployeeProfile.organization_id == org.id,
                EmployeeProfile.is_active.is_(True),
            ).all()

            mailer = get_mailer(org)

            for emp in employees:
                if not emp.email:
                    continue

                # Check if photo request was already sent in the last 60 days
                if emp.photo_request_sent_at and (datetime.utcnow() - emp.photo_request_sent_at).days < 60:
                    continue

                is_due = False
                event_label = ""

                # Check Birthday
                if emp.date_of_birth:
                    dob_match = _effective_birthday_month_day(emp.date_of_birth, target_event_date.year, org.leap_day_policy)
                    if dob_match and dob_match == (target_event_date.month, target_event_date.day):
                        is_due = True
                        event_label = "Birthday"

                # Check Work Anniversary
                if not is_due and emp.date_of_joining:
                    if (emp.date_of_joining.month, emp.date_of_joining.day) == (target_event_date.month, target_event_date.day):
                        years = _years_between(emp.date_of_joining, target_event_date)
                        if years > 0:
                            is_due = True
                            event_label = f"{years}-Year Work Anniversary"

                if is_due:
                    ensure_photo_token(emp, refresh=True)
                    emp.photo_request_sent_at = datetime.utcnow()
                    tdb.commit()

                    subject, html_body = render_photo_request_email(emp, org, event_label, target_event_date)
                    success, error = send_with_retry(mailer, emp.email, subject, html_body)
                    if success:
                        results.append({
                            "employee_id": emp.id,
                            "email": emp.email,
                            "event_label": event_label,
                            "celebration_date": str(target_event_date),
                            "status": "sent",
                        })
                    else:
                        results.append({
                            "employee_id": emp.id,
                            "email": emp.email,
                            "event_label": event_label,
                            "celebration_date": str(target_event_date),
                            "status": "failed",
                            "error": error,
                        })

    db.commit()
    return results
