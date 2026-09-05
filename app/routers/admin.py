from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    DigestLog,
    EmployeeProfile,
    EventLog,
    EventStatus,
    EventTemplate,
    EventType,
    Organization,
    User,
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
    ResendResponse,
    ScanTriggerResponse,
    StatsSummaryResponse,
    TemplateUpdateIn,
    TodayStats,
    UpcomingEventItem,
)
from app.services.audit import record_audit_log
from app.services.csv_importer import import_employees_from_csv
from app.services.demo import reset_demo_organization
from app.services.hrms_sync import sync_employees
from app.services.mailer import get_mailer, send_with_retry
from app.services.pipeline import run_tenant_pipeline
from app.services.renderer import render_event
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
        raise HTTPException(status_code=400, detail="No active organization selected")
    return user, org


def get_current_org(
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
) -> Organization:
    """
    Resolves the tenant Organization.
    """
    _, org = user_and_org
    return org


# ---------------------------------------------------------------------------
# Organization Settings & Profile
# ---------------------------------------------------------------------------


@router.get("/organization", response_model=OrganizationOut)
def get_organization_profile(
    org: Organization = Depends(get_current_org),
):
    return org


@router.patch("/organization", response_model=OrganizationOut)
def update_organization_profile(
    payload: OrganizationUpdateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    user, org = user_and_org
    data = payload.model_dump(exclude_unset=True)
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


# ---------------------------------------------------------------------------
# Demo Sandbox Actions
# ---------------------------------------------------------------------------


@router.post("/demo/reset", response_model=DemoResetResponse)
def reset_demo(
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    """Resets the demo organization with realistic mock employees & fresh scans."""
    user, org = user_and_org
    emp_count, events_detected = reset_demo_organization(db, org.id)
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
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    """
    Manually runs the full pipeline (scan -> render -> send -> digest) for the current organization.
    """
    user, org = user_and_org
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
    db: Session = Depends(get_db),
):
    q = db.query(EventLog).filter(EventLog.organization_id == org.id)
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
    db: Session = Depends(get_db),
):
    event = db.query(EventLog).filter(EventLog.id == event_id, EventLog.organization_id == org.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.employee:
        event.employee_name = event.employee.preferred_name or event.employee.full_name
    return event


@router.post("/events/{event_id}/resend", response_model=ResendResponse)
def resend_event(
    event_id: str,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    user, org = user_and_org
    event = db.query(EventLog).filter(EventLog.id == event_id, EventLog.organization_id == org.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status == EventStatus.SENT:
        return ResendResponse(event_id=event.id, status=event.status, message="Already sent; refusing to resend.")

    if event.status in (EventStatus.PENDING, EventStatus.FAILED) and not event.rendered_html:
        render_event(db, event)
        db.commit()
        if event.status == EventStatus.FAILED:
            return ResendResponse(event_id=event.id, status=event.status, message=event.error_detail or "Render failed")

    employee = event.employee or db.get(EmployeeProfile, event.employee_id)
    if not employee or not employee.email:
        event.status = EventStatus.FAILED
        event.error_detail = "Employee has no email address"
        db.commit()
        return ResendResponse(event_id=event.id, status=event.status, message=event.error_detail)

    mailer = get_mailer(org)
    event.attempt_count += 1
    success, error = send_with_retry(mailer, employee.email, event.rendered_subject, event.rendered_html)
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
    db: Session = Depends(get_db),
):
    q = db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id)
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
    db: Session = Depends(get_db),
):
    emp = db.query(EmployeeProfile).filter(
        EmployeeProfile.id == employee_id,
        EmployeeProfile.organization_id == org.id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    recent_events = (
        db.query(EventLog)
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
        last_synced_at=emp.last_synced_at,
        recent_events=recent_events,
    )


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(
    payload: EmployeeCreateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    user, org = user_and_org
    existing = db.query(EmployeeProfile).filter(
        EmployeeProfile.organization_id == org.id,
        EmployeeProfile.employee_code == payload.employee_code,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee code already exists in this organization")

    emp_data = payload.model_dump()
    emp_data["organization_id"] = org.id
    emp = EmployeeProfile(**emp_data)
    db.add(emp)
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
    db.refresh(emp)
    return emp


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    user, org = user_and_org
    emp = db.query(EmployeeProfile).filter(
        EmployeeProfile.id == employee_id,
        EmployeeProfile.organization_id == org.id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    data = payload.model_dump(exclude_unset=True)
    if "employee_code" in data and data["employee_code"] != emp.employee_code:
        conflict = db.query(EmployeeProfile).filter(
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
    db.commit()
    db.refresh(emp)
    return emp


@router.post("/employees/upload-csv", response_model=CsvImportResponse)
async def upload_employees_csv(
    request: Request,
    file: UploadFile = File(...),
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    """Bulk imports/updates employees via CSV with automatic field mapping."""
    user, org = user_and_org
    content = await file.read()
    imported, updated, failed, raw_errors = import_employees_from_csv(db, org.id, content)

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
    db: Session = Depends(get_db),
):
    return (
        db.query(EventTemplate)
        .filter(EventTemplate.organization_id == org.id)
        .order_by(EventTemplate.event_type.asc(), EventTemplate.variant_key.asc())
        .all()
    )


@router.patch("/templates/{template_id}", response_model=EventTemplateOut)
def update_template(
    template_id: str,
    payload: TemplateUpdateIn,
    request: Request,
    user_and_org: tuple[User, Organization] = Depends(get_current_user_and_org_context),
    db: Session = Depends(get_db),
):
    user, org = user_and_org
    template = db.query(EventTemplate).filter(
        EventTemplate.id == template_id,
        EventTemplate.organization_id == org.id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

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
        details=f"Updated template {template.id} ({template.event_type.value if hasattr(template.event_type, 'value') else template.event_type}/{template.variant_key})",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(template)
    return template


# ---------------------------------------------------------------------------
# Stats Summary
# ---------------------------------------------------------------------------


@router.get("/stats/summary", response_model=StatsSummaryResponse)
def get_stats_summary(
    days: int = Query(default=30, ge=1, le=365),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    total_employees = db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id).count()
    active_employees = (
        db.query(EmployeeProfile)
        .filter(EmployeeProfile.organization_id == org.id, EmployeeProfile.is_active.is_(True))
        .count()
    )
    inactive_employees = total_employees - active_employees

    today = date.today()
    today_batch = today.isoformat()

    # Today's event stats
    today_rows = (
        db.query(EventLog.status, func.count(EventLog.id))
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
        db.query(EventLog.batch_id, EventLog.status, func.count(EventLog.id))
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
        due = find_due_events(db, future_date, organization_id=org.id, leap_day_policy=org.leap_day_policy)
        for e in due:
            if e.employee_id not in emp_cache:
                emp = db.get(EmployeeProfile, e.employee_id)
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
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    created, updated = sync_employees(db)
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
    db: Session = Depends(get_db),
):
    q = db.query(DigestLog).filter(DigestLog.organization_id == org.id)
    total = q.count()
    items = q.order_by(DigestLog.created_at.desc()).offset(offset).limit(limit).all()
    return PaginatedDigestsOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/digests/{batch_id}", response_model=DigestLogOut)
def get_digest(
    batch_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    digest = db.query(DigestLog).filter(
        DigestLog.batch_id == batch_id,
        DigestLog.organization_id == org.id,
    ).first()
    if not digest:
        raise HTTPException(status_code=404, detail="No digest for this batch_id")
    return digest

