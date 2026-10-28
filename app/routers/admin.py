from __future__ import annotations

import csv
import io
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
import shutil
from typing import Iterator
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, func, or_, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import get_db, get_tenant_engine, invalidate_tenant_engine, provision_tenant_database
from app.models import (
    DigestLog,
    EmployeeProfile,
    EventLog,
    EventStatus,
    EventTemplate,
    EventType,
    Organization,
    User,
    UserRole,
)
from app.schemas import (
    CsvImportResponse,
    CsvImportRowError,
    DailyStatsItem,
    DemoResetResponse,
    DigestLogOut,
    EmployeeCreateIn,
    EmployeeDetailOut,
    EmployeeOut,
    EmployeeUpdateIn,
    EventLogOut,
    EventTemplateOut,
    HrmsSyncResponse,
    OrganizationOut,
    OrganizationUpdateIn,
    PaginatedDigestsOut,
    PaginatedEmployeesOut,
    PhotoRequestResponse,
    ResendResponse,
    ScanTriggerResponse,
    StatsSummaryResponse,
    TemplateCreateIn,
    TemplatePreviewIn,
    TemplatePreviewOut,
    TemplateUpdateIn,
    TestDbConnectionIn,
    TestDbConnectionOut,
    TestSmtpConnectionIn,
    TestSmtpConnectionOut,
    TodayStats,
    UpcomingEventItem,
)
from app.services.audit import record_audit_log
from app.services.crypto import decrypt_credential, encrypt_credential
from app.services.csv_importer import import_employees_from_csv
from app.services.demo import reset_demo_organization
from app.services.hrms_sync import sync_employees
from app.services.mailer import SMTPMailer, get_mailer, send_with_retry
from app.services.photo_requester import scan_and_send_advance_photo_requests, send_single_photo_request
from app.services.pipeline import run_tenant_pipeline
from app.services.renderer import preview_template_render, render_event
from app.services.scanner import find_due_events

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


def get_current_user_and_org_context(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> tuple[User, Organization]:
    """
    Resolves both the User and Organization via JWT Bearer Token or API Key.
    """
    from app.routers.auth import get_current_user_and_org
    user, org = get_current_user_and_org(
        authorization=authorization,
        x_api_key=x_api_key,
        x_tenant_id=x_tenant_id,
        db=db,
    )
    if not org:
        raise HTTPException(status_code=400, detail="No tenant selected. Select an organization before using tenant operations.")
    return user, org


def require_write_permission(
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
) -> tuple[User, Organization]:
    """
    Enforces read-only restriction for the Viewer role.
    """
    user, org = user_and_org
    if user.role == UserRole.VIEWER:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Viewer role has read-only access",
        )
    return user, org


def get_current_org(
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
) -> Organization:
    """
    Resolves the tenant Organization.
    """
    _, org = user_and_org
    return org


def get_tenant_db(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Iterator[Session]:
    """
    Yields a database session connected directly to the tenant's dedicated database.
    Tenant operational data is always read from the tenant's dedicated database.
    """
    if not org.is_db_configured:
        raise HTTPException(
            status_code=403,
            detail="You cannot add your data before you configure your database and email provider service.",
        )
    try:
        eng = get_tenant_engine(org)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    TenantSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    session = TenantSession()
    try:
        yield session
    finally:
        session.close()


def check_onboarding_guard(org: Organization) -> None:
    """
    Enforces that an organization has configured their dedicated database and email provider
    before they can insert employee data or run automated scans.
    """
    if not org.is_setup_complete:
        raise HTTPException(
            status_code=403,
            detail="You cannot add your data before you configure your database and email provider service.",
        )


def refresh_onboarding_status(org: Organization) -> bool:
    """
    Evaluates whether an organization has completed setup requirements (DB + Email provider).
    If MAIL_PROVIDER is 'mock' or 'system', DB configuration unlocks onboarding seamlessly.
    """
    has_db = bool(org.is_db_configured or (org.db_host and org.db_name))
    has_smtp = bool(
        org.is_smtp_configured
        or (org.smtp_host and org.smtp_from_address)
        or settings.MAIL_PROVIDER in ("mock", "system")
    )

    if has_db and has_smtp:
        org.is_setup_complete = True
    elif not has_db:
        org.is_setup_complete = False
    return org.is_setup_complete


def _resolve_database_password(password: str | None, org: Organization) -> str:
    resolved_password = password or decrypt_credential(org.db_password)
    if not resolved_password:
        raise HTTPException(
            status_code=400,
            detail="Enter the database password to test or save this connection.",
        )
    return resolved_password


# ---------------------------------------------------------------------------
# Organization Settings & Profile
# ---------------------------------------------------------------------------


@router.get("/organization", response_model=OrganizationOut)
def get_organization_profile(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    refresh_onboarding_status(org)
    db.commit()
    return org


@router.patch("/organization", response_model=OrganizationOut)
def update_organization_profile(
    payload: OrganizationUpdateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    user, org = user_and_org
    data = payload.model_dump(exclude_unset=True)
    if "db_password" in data and data["db_password"]:
        data["db_password"] = encrypt_credential(data["db_password"])
    if "smtp_password" in data and data["smtp_password"]:
        data["smtp_password"] = encrypt_credential(data["smtp_password"])

    for k, v in data.items():
        setattr(org, k, v)

    record_audit_log(
        db,
        action="SETTINGS_UPDATED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        details=f"Updated settings: {', '.join(data.keys())}",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(org)
    return org


@router.post("/settings/test-db", response_model=TestDbConnectionOut)
def test_database_connection(
    payload: TestDbConnectionIn,
    org: Organization = Depends(get_current_org),
):
    """
    Tests connectivity and latency to a tenant's private PostgreSQL database.
    """
    password = _resolve_database_password(payload.db_password, org)
    user_esc = urllib.parse.quote_plus(payload.db_user)
    pwd_esc = urllib.parse.quote_plus(password)
    ssl_param = f"?sslmode={payload.db_ssl_mode}" if payload.db_ssl_mode else ""
    url = f"postgresql+psycopg2://{user_esc}:{pwd_esc}@{payload.db_host}:{payload.db_port}/{payload.db_name}{ssl_param}"

    t0 = time.perf_counter()
    try:
        test_engine = create_engine(url, connect_args={"connect_timeout": 5})
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
        latency = round((time.perf_counter() - t0) * 1000, 2)
        test_engine.dispose()
        return TestDbConnectionOut(
            success=True,
            latency_ms=latency,
            server_version=str(result),
            message=f"Successfully connected to PostgreSQL database ({latency} ms latency).",
        )
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return TestDbConnectionOut(
            success=False,
            latency_ms=latency,
            server_version=None,
            message=f"Connection failed: {exc}",
        )


@router.post("/settings/database", response_model=OrganizationOut)
def save_database_configuration(
    payload: TestDbConnectionIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    """
    Saves PostgreSQL connection credentials, provisions tenant tables, and activates BYODB.
    """
    user, org = user_and_org
    password = _resolve_database_password(payload.db_password, org)

    user_esc = urllib.parse.quote_plus(payload.db_user)
    pwd_esc = urllib.parse.quote_plus(password)
    ssl_param = f"?sslmode={payload.db_ssl_mode}" if payload.db_ssl_mode else ""
    url = f"postgresql+psycopg2://{user_esc}:{pwd_esc}@{payload.db_host}:{payload.db_port}/{payload.db_name}{ssl_param}"

    # Verify connectivity first
    try:
        test_engine = create_engine(url, connect_args={"connect_timeout": 5})
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to connect to PostgreSQL database: {exc}. Please verify credentials and network access.",
        )

    # Invalidate cached engine
    invalidate_tenant_engine(org.id)

    # Update org credentials in platform DB
    org.db_host = payload.db_host.strip()
    org.db_port = payload.db_port
    org.db_name = payload.db_name.strip()
    org.db_user = payload.db_user.strip()
    if payload.db_password:
        org.db_password = encrypt_credential(payload.db_password)
    org.db_ssl_mode = payload.db_ssl_mode
    org.is_db_configured = True

    # Setup status check (requires DB + SMTP or mock mailer)
    refresh_onboarding_status(org)

    # Provision tenant tables directly on target engine
    ok, msg = provision_tenant_database(org, target_engine=test_engine)
    test_engine.dispose()
    if not ok:
        db.rollback()
        status_code = 409 if "already contains a different organization" in msg else 500
        raise HTTPException(
            status_code=status_code,
            detail=f"Database connected, but tenant tables could not be provisioned. {msg}",
        )

    record_audit_log(
        db,
        action="TENANT_DATABASE_CONFIGURED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        details=f"Tenant configured private PostgreSQL database ({org.db_name} on {org.db_host}:{org.db_port})",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(org)
    return org


@router.post("/settings/test-smtp", response_model=TestSmtpConnectionOut)
def test_smtp_connection(
    payload: TestSmtpConnectionIn,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
):
    """
    Tests SMTP connectivity by attempting an SMTP handshake and sending a live test email.
    """
    user, org = user_and_org
    recipient = payload.test_recipient or user.email

    if settings.MAIL_PROVIDER == "mock" or settings.TESTING:
        from app.services.mailer import MockMailer
        mailer = MockMailer()
    else:
        mailer = SMTPMailer(
            host=payload.smtp_host.strip(),
            port=payload.smtp_port,
            username=payload.smtp_username.strip() if payload.smtp_username else None,
            password=payload.smtp_password if payload.smtp_password else None,
            from_address=payload.smtp_from_address.strip(),
            use_tls=payload.smtp_use_tls,
        )

    test_subject = f"Test Email from {org.name} Celebration Hub"
    test_body = f"""
    <div style="font-family: sans-serif; padding: 20px; line-height: 1.5;">
        <h2 style="color: #4f46e5;">SMTP Connection Verified!</h2>
        <p>This is a test notification confirming that your SMTP email settings for <strong>{org.name}</strong> are working perfectly.</p>
        <p style="color: #6b7280; font-size: 12px;">Sent from {payload.smtp_from_address} via {payload.smtp_host}:{payload.smtp_port}</p>
    </div>
    """

    success, error = send_with_retry(mailer, recipient, test_subject, test_body)
    if success:
        return TestSmtpConnectionOut(
            success=True,
            message=f"Test email successfully sent to {recipient} via {payload.smtp_host}:{payload.smtp_port}!",
        )
    return TestSmtpConnectionOut(
        success=False,
        message=f"Failed to send email via SMTP: {error}",
    )


@router.post("/settings/smtp", response_model=OrganizationOut)
def save_smtp_configuration(
    payload: TestSmtpConnectionIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    """
    Saves custom SMTP email configuration, encrypts credentials, and activates mail delivery.
    """
    user, org = user_and_org

    org.smtp_host = payload.smtp_host.strip()
    org.smtp_port = payload.smtp_port
    org.smtp_username = payload.smtp_username.strip() if payload.smtp_username else None
    if payload.smtp_password:
        org.smtp_password = encrypt_credential(payload.smtp_password)
    org.smtp_from_address = payload.smtp_from_address.strip()
    org.smtp_use_tls = payload.smtp_use_tls
    org.is_smtp_configured = True

    # Setup status check (requires DB + SMTP or mock mailer)
    refresh_onboarding_status(org)

    record_audit_log(
        db,
        action="TENANT_SMTP_CONFIGURED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        details=f"Tenant configured custom SMTP ({org.smtp_from_address} on {org.smtp_host}:{org.smtp_port})",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(org)
    return org


# ---------------------------------------------------------------------------
# Demo Sandbox Actions
# ---------------------------------------------------------------------------


@router.post("/demo/reset", response_model=DemoResetResponse)
def reset_demo(
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    """Resets the demo organization with realistic mock employees & fresh scans."""
    user, org = user_and_org
    emp_count, events_detected = reset_demo_organization(tenant_db, org.id)
    org.cached_employee_count = emp_count
    org.cached_event_count = events_detected
    record_audit_log(
        db,
        action="DEMO_RESET",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        details=f"Reset demo data ({emp_count} employees, {events_detected} events)",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return DemoResetResponse(
        success=True,
        message="Demo organization successfully reset with fresh sample data",
        employee_count=emp_count,
        events_detected=events_detected,
    )


# ---------------------------------------------------------------------------
# Pipeline & Scan Trigger
# ---------------------------------------------------------------------------


@router.post("/scan/trigger", response_model=ScanTriggerResponse)
def trigger_scan(
    request: Request,
    scan_date: date | None = Query(default=None, description="Defaults to today"),
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    """
    Manually runs the full pipeline (scan -> render -> send -> digest) for the current organization.
    """
    user, org = user_and_org
    check_onboarding_guard(org)

    result = run_tenant_pipeline(db, org.id, scan_date=scan_date)
    record_audit_log(
        db,
        action="SCAN_TRIGGERED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="pipeline",
        details=f"Scan triggered for date {scan_date or 'today'}: detected {result.detected}, sent {result.sent}, failed {result.failed}",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return ScanTriggerResponse(**result.__dict__)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@router.get("/events", response_model=list[EventLogOut])
def list_events(
    batch_id: str | None = Query(default=None),
    status: EventStatus | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    q = tenant_db.query(EventLog).filter(EventLog.organization_id == org.id)
    if batch_id:
        q = q.filter(EventLog.batch_id == batch_id)
    if status:
        q = q.filter(EventLog.status == status)
    if employee_id:
        q = q.filter(EventLog.employee_id == employee_id)

    events = q.order_by(EventLog.created_at.desc()).limit(500).all()
    for ev in events:
        if ev.employee:
            ev.employee_name = ev.employee.preferred_name or ev.employee.full_name
    return events


@router.get("/events/{event_id}", response_model=EventLogOut)
def get_event(
    event_id: str,
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    event = tenant_db.query(EventLog).filter(EventLog.id == event_id, EventLog.organization_id == org.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.employee:
        event.employee_name = event.employee.preferred_name or event.employee.full_name
    return event


@router.post("/events/{event_id}/resend", response_model=ResendResponse)
def resend_event(
    event_id: str,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    user, org = user_and_org
    event = tenant_db.query(EventLog).filter(EventLog.id == event_id, EventLog.organization_id == org.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status == EventStatus.SENT:
        return ResendResponse(event_id=event.id, status=event.status, message="Already sent; refusing to resend.")

    if event.status in (EventStatus.PENDING, EventStatus.FAILED) and not event.rendered_html:
        render_event(tenant_db, event)
        tenant_db.commit()
        if event.status == EventStatus.FAILED:
            return ResendResponse(event_id=event.id, status=event.status, message=event.error_detail or "Render failed")

    employee = event.employee or tenant_db.get(EmployeeProfile, event.employee_id)
    if not employee or not employee.email:
        event.status = EventStatus.FAILED
        event.error_detail = "Employee has no email address"
        tenant_db.commit()
        return ResendResponse(event_id=event.id, status=event.status, message=event.error_detail)

    mailer = get_mailer(org)
    event.attempt_count += 1
    attachment_path = None
    html_to_send = event.rendered_html or ""
    if getattr(event, "used_custom_photo", False) and employee.photo_url:
        clean_rel = employee.photo_url.lstrip("/").replace("/", os.sep)
        if os.path.isfile(clean_rel):
            attachment_path = clean_rel
        elif os.path.isfile(employee.photo_url):
            attachment_path = employee.photo_url
        if attachment_path:
            html_to_send = html_to_send.replace(employee.photo_url, "cid:celebration_photo")
            html_to_send = html_to_send.replace(f"/{employee.photo_url.lstrip('/')}", "cid:celebration_photo")

    success, error = send_with_retry(
        mailer,
        employee.email,
        event.rendered_subject,
        html_to_send,
        attachment_path=attachment_path,
    )
    if success:
        event.status = EventStatus.SENT
        event.sent_at = datetime.utcnow()
        event.error_detail = None
        msg = "Resent successfully"
    else:
        event.status = EventStatus.FAILED
        event.error_detail = error
        msg = error or "Send failed"

    record_audit_log(
        db,
        action="EVENT_RESENT",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="event",
        resource_id=event.id,
        details=f"Event resend attempt ({event.event_type.value if hasattr(event.event_type, 'value') else event.event_type}): {msg}",
        ip_address=request.client.host if request.client else None,
    )
    tenant_db.commit()
    db.commit()
    return ResendResponse(event_id=event.id, status=event.status, message=msg)


# ---------------------------------------------------------------------------
# Employees & CSV Import
# ---------------------------------------------------------------------------


@router.get("/employees", response_model=PaginatedEmployeesOut)
def list_employees(
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    q = tenant_db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id)
    if is_active is not None:
        q = q.filter(EmployeeProfile.is_active.is_(is_active))
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                EmployeeProfile.full_name.ilike(term),
                EmployeeProfile.preferred_name.ilike(term),
                EmployeeProfile.email.ilike(term),
                EmployeeProfile.employee_code.ilike(term),
                EmployeeProfile.department.ilike(term),
            )
        )
    total = q.count()
    items = q.order_by(EmployeeProfile.full_name.asc()).offset(offset).limit(limit).all()
    return PaginatedEmployeesOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/employees/{employee_id}", response_model=EmployeeDetailOut)
def get_employee(
    employee_id: str,
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    emp = tenant_db.query(EmployeeProfile).filter(
        EmployeeProfile.id == employee_id,
        EmployeeProfile.organization_id == org.id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    recent_events = (
        tenant_db.query(EventLog)
        .filter(EventLog.employee_id == employee_id, EventLog.organization_id == org.id)
        .order_by(EventLog.event_date.desc(), EventLog.created_at.desc())
        .limit(50)
        .all()
    )
    for ev in recent_events:
        ev.employee_name = emp.preferred_name or emp.full_name

    return EmployeeDetailOut(
        id=emp.id,
        organization_id=emp.organization_id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        preferred_name=emp.preferred_name,
        email=emp.email,
        photo_url=emp.photo_url,
        date_of_birth=emp.date_of_birth,
        date_of_joining=emp.date_of_joining,
        department=emp.department,
        manager_id=emp.manager_id,
        team_channel_id=emp.team_channel_id,
        is_active=emp.is_active,
        birthday_template_id=emp.birthday_template_id,
        anniversary_template_id=emp.anniversary_template_id,
        last_synced_at=emp.last_synced_at,
        recent_events=recent_events,
    )


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(
    payload: EmployeeCreateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    user, org = user_and_org
    check_onboarding_guard(org)

    existing = tenant_db.query(EmployeeProfile).filter(
        EmployeeProfile.organization_id == org.id,
        EmployeeProfile.employee_code == payload.employee_code,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee code already exists in this organization")

    if payload.birthday_template_id:
        bt = tenant_db.query(EventTemplate).filter(
            EventTemplate.id == payload.birthday_template_id,
            EventTemplate.organization_id == org.id,
            EventTemplate.event_type == EventType.BIRTHDAY,
        ).first()
        if not bt:
            raise HTTPException(status_code=400, detail="Invalid birthday template selected")

    if payload.anniversary_template_id:
        at = tenant_db.query(EventTemplate).filter(
            EventTemplate.id == payload.anniversary_template_id,
            EventTemplate.organization_id == org.id,
            EventTemplate.event_type == EventType.WORK_ANNIVERSARY,
        ).first()
        if not at:
            raise HTTPException(status_code=400, detail="Invalid anniversary template selected")

    emp_data = payload.model_dump()
    emp_data["organization_id"] = org.id
    emp = EmployeeProfile(**emp_data)
    tenant_db.add(emp)
    tenant_db.commit()
    tenant_db.refresh(emp)

    # Update cached employee count in platform db
    org.cached_employee_count = tenant_db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id).count()
    record_audit_log(
        db,
        action="EMPLOYEE_CREATED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="employee",
        resource_id=emp.id,
        details=f"Created employee {emp.full_name} ({emp.employee_code})",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return emp


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    user, org = user_and_org
    emp = tenant_db.query(EmployeeProfile).filter(
        EmployeeProfile.id == employee_id,
        EmployeeProfile.organization_id == org.id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if payload.birthday_template_id:
        bt = tenant_db.query(EventTemplate).filter(
            EventTemplate.id == payload.birthday_template_id,
            EventTemplate.organization_id == org.id,
            EventTemplate.event_type == EventType.BIRTHDAY,
        ).first()
        if not bt:
            raise HTTPException(status_code=400, detail="Invalid birthday template selected")

    if payload.anniversary_template_id:
        at = tenant_db.query(EventTemplate).filter(
            EventTemplate.id == payload.anniversary_template_id,
            EventTemplate.organization_id == org.id,
            EventTemplate.event_type == EventType.WORK_ANNIVERSARY,
        ).first()
        if not at:
            raise HTTPException(status_code=400, detail="Invalid anniversary template selected")

    data = payload.model_dump(exclude_unset=True)
    if "employee_code" in data and data["employee_code"] != emp.employee_code:
        conflict = tenant_db.query(EmployeeProfile).filter(
            EmployeeProfile.organization_id == org.id,
            EmployeeProfile.employee_code == data["employee_code"],
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Employee code already exists in this organization")

    for k, v in data.items():
        setattr(emp, k, v)

    record_audit_log(
        db,
        action="EMPLOYEE_UPDATED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="employee",
        resource_id=emp.id,
        details=f"Updated employee {emp.full_name} ({', '.join(data.keys())})",
        ip_address=request.client.host if request.client else None,
    )
    tenant_db.commit()
    tenant_db.refresh(emp)
    db.commit()
    return emp


@router.post("/employees/{employee_id}/request-photo", response_model=PhotoRequestResponse)
def request_employee_photo(
    employee_id: str,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    """
    Sends an email to the employee requesting a photo of their choice for their upcoming celebration.
    """
    user, org = user_and_org
    success, message = send_single_photo_request(tenant_db, employee_id, org.id, force=True, org=org)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    record_audit_log(
        db,
        action="PHOTO_REQUEST_SENT",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="employee",
        resource_id=employee_id,
        details=f"Triggered celebration photo request email: {message}",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return PhotoRequestResponse(success=True, message=message)


@router.post("/employees/{employee_id}/upload-photo", response_model=EmployeeOut)
async def upload_employee_photo_admin(
    employee_id: str,
    request: Request,
    file: UploadFile = File(...),
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    """
    Directly uploads or updates an employee photo from the admin dashboard.
    """
    user, org = user_and_org
    emp = tenant_db.query(EmployeeProfile).filter(
        EmployeeProfile.id == employee_id,
        EmployeeProfile.organization_id == org.id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=400, detail=f"Invalid image format '{ext}'. Allowed: JPG, PNG, WEBP, GIF")

    upload_dir = Path("uploads/photos")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex[:12]
    safe_filename = f"{emp.id}_{file_id}{ext}"
    dest_path = upload_dir / safe_filename

    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    emp.photo_url = f"/uploads/photos/{safe_filename}"
    emp.has_custom_photo = True
    tenant_db.commit()
    tenant_db.refresh(emp)

    record_audit_log(
        db,
        action="EMPLOYEE_PHOTO_UPLOADED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="employee",
        resource_id=emp.id,
        details=f"Admin uploaded photo for {emp.full_name}: {emp.photo_url}",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return emp


@router.post("/photo-requests/scan", response_model=list[dict])
def trigger_advance_photo_requests_scan(
    request: Request,
    scan_date: date | None = Query(default=None, description="Defaults to today"),
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    """
    Triggers the advance photo request scan for upcoming celebrations in this organization.
    """
    user, org = user_and_org
    results = scan_and_send_advance_photo_requests(tenant_db, organization_id=org.id, scan_date=scan_date)

    record_audit_log(
        db,
        action="PHOTO_REQUEST_SCAN_TRIGGERED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="photo_requester",
        details=f"Photo request scan completed. Dispatched {len(results)} requests.",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return results


@router.post("/employees/upload-csv", response_model=CsvImportResponse)
async def upload_employees_csv(
    request: Request,
    file: UploadFile = File(...),
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    """Bulk imports/updates employees via CSV with automatic field mapping."""
    user, org = user_and_org
    check_onboarding_guard(org)

    content = await file.read()
    imported, updated, failed, raw_errors = import_employees_from_csv(tenant_db, org.id, content)

    # Update cached employee count in platform db
    org.cached_employee_count = tenant_db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id).count()

    record_audit_log(
        db,
        action="CSV_IMPORTED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="employee",
        details=f"CSV import completed: {imported} imported, {updated} updated, {failed} failed",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    errors = [CsvImportRowError(row=e["row"], error=e["error"]) for e in raw_errors]
    return CsvImportResponse(
        total_rows=imported + updated + failed,
        imported=imported,
        updated=updated,
        failed=failed,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=list[EventTemplateOut])
def list_templates(
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    templates = (
        tenant_db.query(EventTemplate)
        .filter(EventTemplate.organization_id == org.id)
        .order_by(EventTemplate.event_type.asc(), EventTemplate.is_default.desc(), EventTemplate.name.asc())
        .all()
    )
    if not templates:
        from app.seed import seed_default_templates
        seed_default_templates(tenant_db, org.id)
        tenant_db.commit()
        templates = (
            tenant_db.query(EventTemplate)
            .filter(EventTemplate.organization_id == org.id)
            .order_by(EventTemplate.event_type.asc(), EventTemplate.is_default.desc(), EventTemplate.name.asc())
            .all()
        )
    return templates


@router.post("/templates", response_model=EventTemplateOut, status_code=201)
def create_template(
    payload: TemplateCreateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    user, org = user_and_org

    # Generate variant_key if not provided
    import re, uuid
    variant_key = payload.variant_key
    if not variant_key:
        slug_base = re.sub(r"[^a-zA-Z0-9_]+", "_", payload.name.strip().lower())
        variant_key = f"{slug_base}_{uuid.uuid4().hex[:6]}"

    # Validate template syntax with Jinja2 engine
    try:
        preview_template_render(payload.subject_line, payload.html_body, payload.event_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid template syntax: {exc}")

    # If marked as default, unset existing defaults for this event type
    if payload.is_default:
        tenant_db.query(EventTemplate).filter(
            EventTemplate.organization_id == org.id,
            EventTemplate.event_type == payload.event_type,
        ).update({"is_default": False})

    new_tmpl = EventTemplate(
        organization_id=org.id,
        name=payload.name.strip(),
        event_type=payload.event_type,
        variant_key=variant_key,
        subject_line=payload.subject_line,
        html_body=payload.html_body,
        is_active=payload.is_active,
        is_default=payload.is_default,
    )
    tenant_db.add(new_tmpl)
    tenant_db.commit()
    tenant_db.refresh(new_tmpl)

    record_audit_log(
        db,
        action="TEMPLATE_CREATED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="template",
        resource_id=new_tmpl.id,
        details=f"Created template '{new_tmpl.name}' ({new_tmpl.event_type.value}/{new_tmpl.variant_key}, default={new_tmpl.is_default})",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return new_tmpl


@router.patch("/templates/{template_id}", response_model=EventTemplateOut)
def update_template(
    template_id: str,
    payload: TemplateUpdateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    user, org = user_and_org
    template = tenant_db.query(EventTemplate).filter(
        EventTemplate.id == template_id,
        EventTemplate.organization_id == org.id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # If updating subject or body, validate syntax
    test_subject = payload.subject_line if payload.subject_line is not None else template.subject_line
    test_body = payload.html_body if payload.html_body is not None else template.html_body
    try:
        preview_template_render(test_subject, test_body, template.event_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid template syntax: {exc}")

    # If setting is_default=True, unset other defaults for this event type
    if payload.is_default is True:
        tenant_db.query(EventTemplate).filter(
            EventTemplate.organization_id == org.id,
            EventTemplate.event_type == template.event_type,
            EventTemplate.id != template.id,
        ).update({"is_default": False})

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(template, k, v)

    record_audit_log(
        db,
        action="TEMPLATE_UPDATED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="template",
        resource_id=template.id,
        details=f"Updated template '{template.name or template.variant_key}' ({template.event_type.value}/{template.variant_key}, default={template.is_default})",
        ip_address=request.client.host if request.client else None,
    )
    tenant_db.commit()
    tenant_db.refresh(template)
    db.commit()
    return template


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    user, org = user_and_org
    template = tenant_db.query(EventTemplate).filter(
        EventTemplate.id == template_id,
        EventTemplate.organization_id == org.id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_default:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the default template for this event type. Please designate another template as default first before deleting this one.",
        )

    # Disassociate from employees if assigned
    tenant_db.query(EmployeeProfile).filter(
        EmployeeProfile.organization_id == org.id,
        EmployeeProfile.birthday_template_id == template.id,
    ).update({"birthday_template_id": None})

    tenant_db.query(EmployeeProfile).filter(
        EmployeeProfile.organization_id == org.id,
        EmployeeProfile.anniversary_template_id == template.id,
    ).update({"anniversary_template_id": None})

    record_audit_log(
        db,
        action="TEMPLATE_DELETED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=org.id,
        resource_type="template",
        resource_id=template.id,
        details=f"Deleted template '{template.name or template.variant_key}' ({template.event_type.value}/{template.variant_key})",
        ip_address=request.client.host if request.client else None,
    )

    tenant_db.delete(template)
    tenant_db.commit()
    db.commit()
    return {"message": "Template successfully deleted", "template_id": template_id}


@router.post("/templates/preview", response_model=TemplatePreviewOut)
def preview_template(
    payload: TemplatePreviewIn,
    org: Organization = Depends(get_current_org),
):
    try:
        custom_ctx = {
            "company_name": org.name,
            "company_logo_url": org.company_logo_url,
        }
        rendered_subject, rendered_html = preview_template_render(
            subject_line=payload.subject_line,
            html_body=payload.html_body,
            event_type=payload.event_type,
            custom_context=custom_ctx,
        )
        return TemplatePreviewOut(
            rendered_subject=rendered_subject,
            rendered_html=rendered_html,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Stats Summary
# ---------------------------------------------------------------------------


@router.get("/stats/summary", response_model=StatsSummaryResponse)
def get_stats_summary(
    days: int = Query(default=30, ge=1, le=365),
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    total_employees = tenant_db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id).count()
    active_employees = (
        tenant_db.query(EmployeeProfile)
        .filter(EmployeeProfile.organization_id == org.id, EmployeeProfile.is_active.is_(True))
        .count()
    )
    inactive_employees = total_employees - active_employees

    today = date.today()
    today_batch = today.isoformat()

    # Today's event stats
    today_rows = (
        tenant_db.query(EventLog.status, func.count(EventLog.id))
        .filter(EventLog.organization_id == org.id, EventLog.batch_id == today_batch)
        .group_by(EventLog.status)
        .all()
    )
    today_counts = {status: count for status, count in today_rows}
    today_stats = TodayStats(
        sent=today_counts.get(EventStatus.SENT, 0),
        failed=today_counts.get(EventStatus.FAILED, 0),
        pending=today_counts.get(EventStatus.PENDING, 0),
        skipped=today_counts.get(EventStatus.SKIPPED, 0),
    )

    # Daily stats over last `days` days
    start_date = today - timedelta(days=days - 1)
    date_counts: dict[str, dict[EventStatus, int]] = {}

    log_rows = (
        tenant_db.query(EventLog.batch_id, EventLog.status, func.count(EventLog.id))
        .filter(
            EventLog.organization_id == org.id,
            EventLog.event_date >= start_date,
            EventLog.event_date <= today,
        )
        .group_by(EventLog.batch_id, EventLog.status)
        .all()
    )
    for b_id, st, cnt in log_rows:
        date_counts.setdefault(b_id, {})[st] = cnt

    daily_stats: list[DailyStatsItem] = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        d_str = d.isoformat()
        st_map = date_counts.get(d_str, {})
        daily_stats.append(
            DailyStatsItem(
                date=d_str,
                batch_id=d_str,
                sent=st_map.get(EventStatus.SENT, 0),
                failed=st_map.get(EventStatus.FAILED, 0),
                pending=st_map.get(EventStatus.PENDING, 0),
                skipped=st_map.get(EventStatus.SKIPPED, 0),
            )
        )

    # Upcoming events in next 7 days
    upcoming_events_7d: list[UpcomingEventItem] = []
    emp_cache: dict[str, EmployeeProfile] = {}
    for i in range(1, 8):
        future_date = today + timedelta(days=i)
        due = find_due_events(tenant_db, future_date, organization_id=org.id, leap_day_policy=org.leap_day_policy)
        for e in due:
            if e.employee_id not in emp_cache:
                emp = tenant_db.get(EmployeeProfile, e.employee_id)
                if emp:
                    emp_cache[e.employee_id] = emp
            emp_obj = emp_cache.get(e.employee_id)
            if emp_obj:
                upcoming_events_7d.append(
                    UpcomingEventItem(
                        employee_id=emp_obj.id,
                        employee_name=emp_obj.preferred_name or emp_obj.full_name,
                        preferred_name=emp_obj.preferred_name,
                        photo_url=emp_obj.photo_url,
                        department=emp_obj.department,
                        event_type=e.event_type,
                        event_date=e.event_date,
                        years=e.years,
                    )
                )

    return StatsSummaryResponse(
        total_employees=total_employees,
        active_employees=active_employees,
        inactive_employees=inactive_employees,
        today_stats=today_stats,
        upcoming_events_7d=upcoming_events_7d,
        daily_stats=daily_stats,
    )


# ---------------------------------------------------------------------------
# HRMS Sync
# ---------------------------------------------------------------------------


@router.post("/hrms-sync/trigger", response_model=HrmsSyncResponse)
def trigger_hrms_sync(
    user_and_org: tuple[User, Organization] = Depends(require_write_permission),
    db: Session = Depends(get_db),
    tenant_db: Session = Depends(get_tenant_db),
):
    _, org = user_and_org
    check_onboarding_guard(org)

    created, updated = sync_employees(tenant_db)
    org.cached_employee_count = tenant_db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id).count()
    db.commit()
    return HrmsSyncResponse(
        created=created,
        updated=updated,
        message=f"HRMS sync completed: {created} created, {updated} updated",
    )


# ---------------------------------------------------------------------------
# Digests
# ---------------------------------------------------------------------------


@router.get("/digests", response_model=PaginatedDigestsOut)
def list_digests(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    q = tenant_db.query(DigestLog).filter(DigestLog.organization_id == org.id)
    total = q.count()
    items = q.order_by(DigestLog.created_at.desc()).offset(offset).limit(limit).all()
    return PaginatedDigestsOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/digests/{batch_id}", response_model=DigestLogOut)
def get_digest(
    batch_id: str,
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    digest = tenant_db.query(DigestLog).filter(
        DigestLog.batch_id == batch_id,
        DigestLog.organization_id == org.id,
    ).first()
    if not digest:
        raise HTTPException(status_code=404, detail="No digest for this batch_id")
    return digest


# ---------------------------------------------------------------------------
# Executive Reports & CSV Data Exports
# ---------------------------------------------------------------------------


@router.get("/reports/events/export")
def export_events_csv(
    batch_id: str | None = Query(default=None),
    status: EventStatus | None = Query(default=None),
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    """
    Exports celebration event logs as a CSV file for HR compliance and executive audit reporting.
    """
    q = tenant_db.query(EventLog).filter(EventLog.organization_id == org.id)
    if batch_id:
        q = q.filter(EventLog.batch_id == batch_id)
    if status:
        q = q.filter(EventLog.status == status)

    events = q.order_by(EventLog.event_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID",
        "Batch ID",
        "Event Type",
        "Employee Code",
        "Employee Name",
        "Employee Email",
        "Event Date",
        "Tenure Years",
        "Status",
        "Attempt Count",
        "Error Detail",
        "Sent At",
        "Created At",
    ])

    for ev in events:
        emp_name = ev.employee.full_name if ev.employee else ""
        emp_code = ev.employee.employee_code if ev.employee else ""
        emp_email = ev.employee.email if ev.employee else ""
        writer.writerow([
            ev.id,
            ev.batch_id,
            ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
            emp_code,
            emp_name,
            emp_email,
            ev.event_date.isoformat() if ev.event_date else "",
            ev.years or "",
            ev.status.value if hasattr(ev.status, "value") else str(ev.status),
            ev.attempt_count,
            ev.error_detail or "",
            ev.sent_at.isoformat() if ev.sent_at else "",
            ev.created_at.isoformat() if ev.created_at else "",
        ])

    output.seek(0)
    filename = f"{org.slug}_celebration_events_{date.today().isoformat()}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/reports/employees/export")
def export_employees_csv(
    is_active: bool | None = Query(default=None),
    org: Organization = Depends(get_current_org),
    tenant_db: Session = Depends(get_tenant_db),
):
    """
    Exports employee roster and celebration metadata as a CSV file.
    """
    q = tenant_db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id)
    if is_active is not None:
        q = q.filter(EmployeeProfile.is_active.is_(is_active))

    employees = q.order_by(EmployeeProfile.full_name.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Employee ID",
        "Employee Code",
        "Full Name",
        "Preferred Name",
        "Email",
        "Date of Birth",
        "Date of Joining",
        "Department",
        "Is Active",
        "Last Synced At",
    ])

    for emp in employees:
        writer.writerow([
            emp.id,
            emp.employee_code,
            emp.full_name,
            emp.preferred_name or "",
            emp.email,
            emp.date_of_birth.isoformat() if emp.date_of_birth else "",
            emp.date_of_joining.isoformat() if emp.date_of_joining else "",
            emp.department or "",
            "True" if emp.is_active else "False",
            emp.last_synced_at.isoformat() if emp.last_synced_at else "",
        ])

    output.seek(0)
    filename = f"{org.slug}_employee_roster_{date.today().isoformat()}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
