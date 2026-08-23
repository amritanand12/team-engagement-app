from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import DigestLog, EmployeeProfile, EventLog, EventStatus, EventTemplate, EventType
from app.schemas import (
    DailyStatsItem,
    DigestLogOut,
    EmployeeCreateIn,
    EmployeeDetailOut,
    EmployeeOut,
    EmployeeUpdateIn,
    EventLogOut,
    EventTemplateOut,
    HrmsSyncResponse,
    PaginatedDigestsOut,
    PaginatedEmployeesOut,
    ResendResponse,
    ScanTriggerResponse,
    StatsSummaryResponse,
    TemplateUpdateIn,
    TodayStats,
    UpcomingEventItem,
)
from app.services.hrms_sync import sync_employees
from app.services.mailer import get_mailer, send_with_retry
from app.services.pipeline import run_daily_pipeline
from app.services.renderer import render_event
from app.services.scanner import find_due_events

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


def require_admin_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key")


# ---------------------------------------------------------------------------
# Pipeline & Scan Trigger
# ---------------------------------------------------------------------------


@router.post("/scan/trigger", response_model=ScanTriggerResponse, dependencies=[Depends(require_admin_key)])
def trigger_scan(
    scan_date: date | None = Query(default=None, description="Defaults to today"),
    db: Session = Depends(get_db),
):
    """
    Manually runs the full pipeline (scan -> render -> send -> digest) for a given
    date. Uses the exact same code path as the scheduled job, so this is also
    the right tool for re-running a failed day or backfilling a missed one.
    """
    result = run_daily_pipeline(db, scan_date=scan_date)
    return ScanTriggerResponse(**result.__dict__)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@router.get("/events", response_model=list[EventLogOut], dependencies=[Depends(require_admin_key)])
def list_events(
    batch_id: str | None = Query(default=None),
    status: EventStatus | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(EventLog)
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


@router.get("/events/{event_id}", response_model=EventLogOut, dependencies=[Depends(require_admin_key)])
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.get(EventLog, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.employee:
        event.employee_name = event.employee.preferred_name or event.employee.full_name
    return event


@router.post("/events/{event_id}/resend", response_model=ResendResponse, dependencies=[Depends(require_admin_key)])
def resend_event(event_id: str, db: Session = Depends(get_db)):
    """
    Retries a FAILED event. If it was never rendered, renders first. Sending an
    already-SENT event is refused to avoid double-emailing someone.
    """
    event = db.get(EventLog, event_id)
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

    mailer = get_mailer()
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

    db.commit()
    return ResendResponse(event_id=event.id, status=event.status, message=msg)


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------


@router.get("/employees", response_model=PaginatedEmployeesOut, dependencies=[Depends(require_admin_key)])
def list_employees(
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(EmployeeProfile)
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


@router.get("/employees/{employee_id}", response_model=EmployeeDetailOut, dependencies=[Depends(require_admin_key)])
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = db.get(EmployeeProfile, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    recent_events = (
        db.query(EventLog)
        .filter(EventLog.employee_id == employee_id)
        .order_by(EventLog.event_date.desc(), EventLog.created_at.desc())
        .limit(50)
        .all()
    )
    for ev in recent_events:
        ev.employee_name = emp.preferred_name or emp.full_name

    return EmployeeDetailOut(
        id=emp.id,
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


@router.post("/employees", response_model=EmployeeOut, status_code=201, dependencies=[Depends(require_admin_key)])
def create_employee(payload: EmployeeCreateIn, db: Session = Depends(get_db)):
    existing = db.query(EmployeeProfile).filter(EmployeeProfile.employee_code == payload.employee_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee code already exists")

    emp = EmployeeProfile(**payload.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@router.patch("/employees/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(require_admin_key)])
def update_employee(employee_id: str, payload: EmployeeUpdateIn, db: Session = Depends(get_db)):
    emp = db.get(EmployeeProfile, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    data = payload.model_dump(exclude_unset=True)
    if "employee_code" in data and data["employee_code"] != emp.employee_code:
        conflict = db.query(EmployeeProfile).filter(EmployeeProfile.employee_code == data["employee_code"]).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Employee code already exists")

    for k, v in data.items():
        setattr(emp, k, v)

    db.commit()
    db.refresh(emp)
    return emp


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=list[EventTemplateOut], dependencies=[Depends(require_admin_key)])
def list_templates(db: Session = Depends(get_db)):
    return db.query(EventTemplate).order_by(EventTemplate.event_type.asc(), EventTemplate.variant_key.asc()).all()


@router.patch("/templates/{template_id}", response_model=EventTemplateOut, dependencies=[Depends(require_admin_key)])
def update_template(template_id: str, payload: TemplateUpdateIn, db: Session = Depends(get_db)):
    template = db.get(EventTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.is_active = payload.is_active
    db.commit()
    db.refresh(template)
    return template


# ---------------------------------------------------------------------------
# Stats Summary
# ---------------------------------------------------------------------------


@router.get("/stats/summary", response_model=StatsSummaryResponse, dependencies=[Depends(require_admin_key)])
def get_stats_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    total_employees = db.query(EmployeeProfile).count()
    active_employees = db.query(EmployeeProfile).filter(EmployeeProfile.is_active.is_(True)).count()
    inactive_employees = total_employees - active_employees

    today = date.today()
    today_batch = today.isoformat()

    # Today's event stats
    today_rows = db.query(EventLog.status, func.count(EventLog.id)).filter(EventLog.batch_id == today_batch).group_by(EventLog.status).all()
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
        .filter(EventLog.event_date >= start_date, EventLog.event_date <= today)
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

    # Upcoming events in next 7 days (today + 1 to today + 7)
    upcoming_events_7d: list[UpcomingEventItem] = []
    emp_cache: dict[str, EmployeeProfile] = {}
    for i in range(1, 8):
        future_date = today + timedelta(days=i)
        due = find_due_events(db, future_date)
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


@router.post("/hrms-sync/trigger", response_model=HrmsSyncResponse, dependencies=[Depends(require_admin_key)])
def trigger_hrms_sync(db: Session = Depends(get_db)):
    created, updated = sync_employees(db)
    return HrmsSyncResponse(
        created=created,
        updated=updated,
        message=f"HRMS sync completed: {created} created, {updated} updated",
    )


# ---------------------------------------------------------------------------
# Digests
# ---------------------------------------------------------------------------


@router.get("/digests", response_model=PaginatedDigestsOut, dependencies=[Depends(require_admin_key)])
def list_digests(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(DigestLog)
    total = q.count()
    items = q.order_by(DigestLog.created_at.desc()).offset(offset).limit(limit).all()
    return PaginatedDigestsOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/digests/{batch_id}", response_model=DigestLogOut, dependencies=[Depends(require_admin_key)])
def get_digest(batch_id: str, db: Session = Depends(get_db)):
    digest = db.query(DigestLog).filter(DigestLog.batch_id == batch_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="No digest for this batch_id")
    return digest
