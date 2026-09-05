from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class EventType(str, enum.Enum):
    BIRTHDAY = "birthday"
    WORK_ANNIVERSARY = "work_anniversary"


class EventStatus(str, enum.Enum):
    PENDING = "pending"       # detected by scanner, not yet rendered
    RENDERED = "rendered"     # template resolved, ready to send
    SENT = "sent"              # individual email delivered
    FAILED = "failed"          # rendering or delivery failed permanently
    SKIPPED = "skipped"        # deliberately excluded (inactive, policy, etc.)


class DigestStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    EMPTY_SKIPPED = "empty_skipped"


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    HR_MANAGER = "hr_manager"
    VIEWER = "viewer"


class User(Base):
    """
    Authenticated dashboard user. Can be a Platform SuperAdmin (no organization_id)
    or a Tenant Admin / HR Manager / Viewer bound to a specific organization.
    """
    __tablename__ = "app_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organization.id", ondelete="CASCADE"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.TENANT_ADMIN, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization: Mapped["Organization | None"] = relationship()


class Organization(Base):
    """
    Tenant entity. Each organization represents a distinct client company with
    its own settings, branding, templates, employee roster, and delivery channels.
    """
    __tablename__ = "organization"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    company_logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    business_timezone: Mapped[str] = mapped_column(String(100), default="Asia/Kolkata")
    leap_day_policy: Mapped[str] = mapped_column(String(20), default="feb28")  # feb28, mar1, leap_only
    digest_channel_id: Mapped[str] = mapped_column(String(255), default="general")

    # Custom SMTP settings (optional, defaults to system mailer)
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, default=587, nullable=True)
    smtp_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Webhook channels
    slack_webhook_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    teams_webhook_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmployeeProfile(Base):
    """
    Tenant-scoped read-only mirror of HRMS employee data.
    """
    __tablename__ = "employee_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization.id", ondelete="CASCADE"), index=True
    )
    employee_code: Mapped[str] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    preferred_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date, nullable=True)

    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("employee_profile.id"), nullable=True
    )
    team_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint("organization_id", "employee_code", name="uq_org_employee_code"),
        Index("ix_emp_org_dob", "organization_id", "date_of_birth"),
        Index("ix_emp_org_doj", "organization_id", "date_of_joining"),
    )


class EventTemplate(Base):
    """
    Tenant-scoped static templates with Jinja2 placeholders.
    """
    __tablename__ = "event_template"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), index=True)
    variant_key: Mapped[str] = mapped_column(String(64), default="default")
    subject_line: Mapped[str] = mapped_column(String(500))
    html_body: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint("organization_id", "event_type", "variant_key", "is_active", name="uq_org_template_variant_active"),
    )


class EventLog(Base):
    """
    One row per (organization, employee, event_type, event_date).
    Unique constraint ensures complete idempotency across retries and re-runs.
    """
    __tablename__ = "event_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employee_profile.id"), index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    years: Mapped[int | None] = mapped_column(nullable=True)  # years of service, for anniversaries

    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("event_template.id"), nullable=True)
    rendered_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rendered_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.PENDING, index=True)
    batch_id: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD of the scan that created it

    attempt_count: Mapped[int] = mapped_column(default=0)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee: Mapped["EmployeeProfile"] = relationship()
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint("organization_id", "employee_id", "event_type", "event_date", name="uq_org_employee_event_date"),
        Index("ix_event_log_org_batch", "organization_id", "batch_id"),
    )


class DigestLog(Base):
    """One row per batch (day) per organization representing the team digest."""
    __tablename__ = "digest_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization.id", ondelete="CASCADE"), index=True
    )
    batch_id: Mapped[str] = mapped_column(String(10), index=True)
    channel_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[DigestStatus] = mapped_column(Enum(DigestStatus), default=DigestStatus.PENDING)
    rendered_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_count: Mapped[int] = mapped_column(default=0)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint("organization_id", "batch_id", name="uq_org_digest_batch"),
    )


class AuditLog(Base):
    """
    Administrative and security audit trail.
    Tracks authentication, tenant provisioning, configuration changes, and pipeline triggers.
    """
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organization.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255), index=True)
    actor_role: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    organization: Mapped["Organization | None"] = relationship()

    @property
    def organization_name(self) -> str | None:
        return self.organization.name if self.organization else None
