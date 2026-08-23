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


class EmployeeProfile(Base):
    """
    Read-only local mirror of HRMS employee data. HRMS remains the source of truth;
    this table exists so the daily scan doesn't depend on HRMS uptime/rate limits.
    """
    __tablename__ = "employee_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
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

    __table_args__ = (
        Index("ix_employee_dob_month_day", "date_of_birth"),
        Index("ix_employee_doj_month_day", "date_of_joining"),
    )


class EventTemplate(Base):
    """
    Static templates with Jinja2 placeholders. No free-text generation happens here —
    this is pure substitution against a fixed, reviewed layout.
    """
    __tablename__ = "event_template"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), index=True)
    variant_key: Mapped[str] = mapped_column(String(64), default="default")
    subject_line: Mapped[str] = mapped_column(String(500))
    html_body: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("event_type", "variant_key", "is_active", name="uq_template_variant_active"),
    )


class EventLog(Base):
    """
    One row per (employee, event_type, event_date). The unique constraint is what
    makes the whole pipeline idempotent under re-runs and retries.
    """
    __tablename__ = "event_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
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

    __table_args__ = (
        UniqueConstraint("employee_id", "event_type", "event_date", name="uq_employee_event_date"),
    )


class DigestLog(Base):
    """One row per batch (day) representing the team/company-wide digest message."""
    __tablename__ = "digest_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    channel_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[DigestStatus] = mapped_column(Enum(DigestStatus), default=DigestStatus.PENDING)
    rendered_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_count: Mapped[int] = mapped_column(default=0)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
