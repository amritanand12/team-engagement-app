from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import DigestStatus, EventStatus, EventType

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None = None
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
    birthday_template_id: str | None = None
    anniversary_template_id: str | None = None
    has_custom_photo: bool = False
    photo_request_sent_at: datetime | None = None
    photo_upload_token: str | None = None
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
    birthday_template_id: str | None = None
    anniversary_template_id: str | None = None
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
    birthday_template_id: str | None = None
    anniversary_template_id: str | None = None
    has_custom_photo: bool | None = None
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
    organization_id: str | None = None
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
    used_custom_photo: bool = False
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
    organization_id: str | None = None
    event_type: EventType
    name: str | None = ""
    variant_key: str
    subject_line: str
    html_body: str
    is_active: bool
    is_default: bool = False
    created_at: datetime


class TemplateCreateIn(BaseModel):
    name: str
    event_type: EventType
    subject_line: str
    html_body: str
    variant_key: str | None = None
    is_default: bool = False
    is_active: bool = True


class TemplateUpdateIn(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    subject_line: str | None = None
    html_body: str | None = None


class TemplatePreviewIn(BaseModel):
    subject_line: str
    html_body: str
    event_type: EventType


class TemplatePreviewOut(BaseModel):
    rendered_subject: str
    rendered_html: str


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
    organization_id: str | None = None
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


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    api_key: str
    company_logo_url: str | None = None
    business_timezone: str
    leap_day_policy: str
    digest_channel_id: str
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_ssl_mode: str | None = None
    is_db_configured: bool = False
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_from_address: str | None = None
    smtp_use_tls: bool = True
    is_smtp_configured: bool = False
    is_setup_complete: bool = False
    cached_employee_count: int = 0
    cached_event_count: int = 0
    slack_webhook_url: str | None = None
    teams_webhook_url: str | None = None
    photo_request_enabled: bool = True
    photo_request_days_ahead: int = 7
    google_form_url: str | None = None
    is_active: bool
    is_demo: bool
    created_at: datetime


class OrganizationUpdateIn(BaseModel):
    name: str | None = None
    company_logo_url: str | None = None
    business_timezone: str | None = None
    leap_day_policy: str | None = None
    digest_channel_id: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_ssl_mode: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    smtp_use_tls: bool | None = None
    slack_webhook_url: str | None = None
    teams_webhook_url: str | None = None
    photo_request_enabled: bool | None = None
    photo_request_days_ahead: int | None = None
    google_form_url: str | None = None


class PhotoRequestResponse(BaseModel):
    success: bool
    message: str


class TestDbConnectionIn(BaseModel):
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str
    db_ssl_mode: str = "prefer"


class TestDbConnectionOut(BaseModel):
    success: bool
    latency_ms: float | None = None
    server_version: str | None = None
    message: str


class TestSmtpConnectionIn(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str
    smtp_use_tls: bool = True
    test_recipient: str | None = None


class TestSmtpConnectionOut(BaseModel):
    success: bool
    message: str


class OrganizationCreateIn(BaseModel):
    name: str
    slug: str | None = None
    company_logo_url: str | None = None
    business_timezone: str = "Asia/Kolkata"
    leap_day_policy: str = "feb28"
    is_demo: bool = False


class CsvImportRowError(BaseModel):
    row: int
    error: str


class CsvImportResponse(BaseModel):
    total_rows: int
    imported: int
    updated: int
    failed: int
    errors: list[CsvImportRowError] = []


class DemoResetResponse(BaseModel):
    success: bool
    message: str
    employee_count: int
    events_detected: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    organization_id: str | None = None
    is_active: bool
    created_at: datetime


class LoginIn(BaseModel):
    email: str
    password: str


class ApiKeyLoginIn(BaseModel):
    api_key: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    organization: OrganizationOut | None = None


class SuperAdminOrgOut(BaseModel):
    id: str
    name: str
    slug: str
    api_key: str
    company_logo_url: str | None = None
    business_timezone: str
    is_active: bool
    is_demo: bool
    employee_count: int | None
    event_count: int | None
    is_db_configured: bool
    is_smtp_configured: bool
    is_setup_complete: bool
    database_status: str
    last_sync_at: datetime | None = None
    created_at: datetime


class CreateTenantIn(BaseModel):
    name: str
    slug: str | None = None
    admin_email: str
    admin_name: str
    admin_password: str
    business_timezone: str = "Asia/Kolkata"
    leap_day_policy: str = "feb28"


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


class ResetPasswordIn(BaseModel):
    new_password: str


class ChangePasswordResponse(BaseModel):
    success: bool
    message: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None = None
    organization_name: str | None = None
    actor_id: str | None = None
    actor_email: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None = None
    details: str | None = None
    ip_address: str | None = None
    created_at: datetime


class PaginatedAuditLogsOut(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int

