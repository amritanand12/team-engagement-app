from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import DigestStatus, EventStatus, EventType

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_code: str
    full_name: str
    preferred_name: str | None = None
    email: str
    photo_url: str | None = None
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    department: str | None = None
    manager_id: str | None = None
    team_channel_id: str | None = None
    is_active: bool = True
    last_synced_at: datetime | None = None


class EmployeeCreateIn(BaseModel):
    employee_code: str
    full_name: str
    preferred_name: str | None = None
    email: str
    photo_url: str | None = None
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    department: str | None = None
    manager_id: str | None = None
    team_channel_id: str | None = None
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email address format")
        return v

    @field_validator("employee_code", "full_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v


class EmployeeUpdateIn(BaseModel):
    employee_code: str | None = None
    full_name: str | None = None
    preferred_name: str | None = None
    email: str | None = None
    photo_url: str | None = None
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    department: str | None = None
    manager_id: str | None = None
    team_channel_id: str | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not EMAIL_REGEX.match(v):
                raise ValueError("Invalid email address format")
        return v

    @field_validator("employee_code", "full_name")
    @classmethod
    def validate_non_empty(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty")
        return v


class PaginatedEmployeesOut(BaseModel):
    items: list[EmployeeOut]
    total: int
    limit: int
    offset: int


class EventLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    event_type: EventType
    event_date: date
    years: int | None = None
    status: EventStatus
    batch_id: str
    attempt_count: int = 0
    error_detail: str | None = None
    rendered_subject: str | None = None
    rendered_html: str | None = None
    sent_at: datetime | None = None
    created_at: datetime
    employee_name: str | None = None


class EmployeeDetailOut(EmployeeOut):
    recent_events: list[EventLogOut] = []


class ScanTriggerResponse(BaseModel):
    batch_id: str
    detected: int
    rendered: int
    sent: int
    failed: int
    skipped: int
    digest_status: str


class ResendResponse(BaseModel):
    event_id: str
    status: EventStatus
    message: str


class EventTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: EventType
    variant_key: str
    subject_line: str
    html_body: str
    is_active: bool
    created_at: datetime


class TemplateUpdateIn(BaseModel):
    is_active: bool


class DailyStatsItem(BaseModel):
    date: str
    batch_id: str
    sent: int = 0
    failed: int = 0
    pending: int = 0
    skipped: int = 0


class UpcomingEventItem(BaseModel):
    employee_id: str
    employee_name: str
    preferred_name: str | None = None
    photo_url: str | None = None
    department: str | None = None
    event_type: EventType
    event_date: date
    years: int | None = None


class TodayStats(BaseModel):
    sent: int = 0
    failed: int = 0
    pending: int = 0
    skipped: int = 0


class StatsSummaryResponse(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    today_stats: TodayStats
    upcoming_events_7d: list[UpcomingEventItem]
    daily_stats: list[DailyStatsItem]


class DigestLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    channel_id: str
    status: DigestStatus
    rendered_html: str | None = None
    event_count: int = 0
    error_detail: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class PaginatedDigestsOut(BaseModel):
    items: list[DigestLogOut]
    total: int
    limit: int
    offset: int


class HrmsSyncResponse(BaseModel):
    created: int
    updated: int
    message: str
