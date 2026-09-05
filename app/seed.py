"""Seeds the four default templates. Safe to run repeatedly (idempotent by variant_key)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EventTemplate, EventType, Organization, User, UserRole
from app.services.auth import hash_password
from app.services.renderer import load_seed_template_file

settings = get_settings()

DEFAULT_TEMPLATES = [
    dict(
        name="Standard Birthday Celebration",
        event_type=EventType.BIRTHDAY,
        variant_key="default",
        subject_line="🎉 Happy Birthday, {{ name }}!",
        filename="birthday_default.html",
        is_default=True,
    ),
    dict(
        name="Standard Work Anniversary",
        event_type=EventType.WORK_ANNIVERSARY,
        variant_key="anniversary_default",
        subject_line="🎊 Congrats on {{ years }} year{{ 's' if years != 1 else '' }}, {{ name }}!",
        filename="anniversary_default.html",
        is_default=True,
    ),
    dict(
        name="5-Year Milestone Celebration",
        event_type=EventType.WORK_ANNIVERSARY,
        variant_key="anniversary_5yr",
        subject_line="🏅 {{ name }}, 5 years at {{ company_name }}!",
        filename="anniversary_5yr.html",
        is_default=False,
    ),
    dict(
        name="10-Year Decade Celebration",
        event_type=EventType.WORK_ANNIVERSARY,
        variant_key="anniversary_10yr",
        subject_line="👑 {{ name }}, a decade at {{ company_name }}!",
        filename="anniversary_10yr.html",
        is_default=False,
    ),
]


def seed_default_templates(db: Session, organization_id: str) -> int:
    """Seeds the four default templates for a specific organization."""
    created = 0
    for tpl in DEFAULT_TEMPLATES:
        existing = (
            db.query(EventTemplate)
            .filter(
                EventTemplate.organization_id == organization_id,
                EventTemplate.event_type == tpl["event_type"],
                EventTemplate.variant_key == tpl["variant_key"],
            )
            .first()
        )
        if existing:
            if not existing.name:
                existing.name = tpl["name"]
            if tpl.get("is_default") and not existing.is_default:
                existing.is_default = True
            continue
        html_body = load_seed_template_file(tpl["filename"])
        db.add(
            EventTemplate(
                organization_id=organization_id,
                name=tpl["name"],
                event_type=tpl["event_type"],
                variant_key=tpl["variant_key"],
                subject_line=tpl["subject_line"],
                html_body=html_body,
                is_active=True,
                is_default=tpl.get("is_default", False),
            )
        )
        created += 1
    db.commit()
    return created


def seed_superadmin(db: Session) -> User:
    """
    Seeds the platform SuperAdmin account if one does not already exist.
    Guarantees no client organizations, demo sandboxes, or fake users are created.
    """
    superadmin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
    if not superadmin:
        superadmin = db.query(User).filter(User.email == "admin@platform.local").first()

    if not superadmin:
        superadmin = User(
            email="admin@platform.local",
            full_name="Platform SuperAdmin",
            password_hash=hash_password("admin123"),
            role=UserRole.SUPER_ADMIN,
            organization_id=None,
            is_active=True,
        )
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)

    return superadmin


def seed_default_users(db: Session, default_org_id: str) -> None:
    """Seeds the default platform SuperAdmin and default Tenant Admin if they do not exist."""
    seed_superadmin(db)

    # Tenant Admin for the specified org
    tenant_admin = db.query(User).filter(User.email == "admin@acme.com").first()
    if not tenant_admin:
        tenant_admin = User(
            email="admin@acme.com",
            full_name="Acme Admin",
            password_hash=hash_password("acme123"),
            role=UserRole.TENANT_ADMIN,
            organization_id=default_org_id,
            is_active=True,
        )
        db.add(tenant_admin)

    db.commit()


def seed_default_organization(db: Session) -> Organization:
    """
    Ensures a primary organization exists matching ADMIN_API_KEY (used by test fixtures).
    Sets is_demo=False so it is treated as a clean standard client organization.
    """
    org = db.query(Organization).filter(Organization.api_key == settings.ADMIN_API_KEY).first()
    if not org:
        org = db.query(Organization).filter(Organization.slug == "default").first()

    if not org:
        org = Organization(
            name=settings.COMPANY_NAME,
            slug="default",
            api_key=settings.ADMIN_API_KEY,
            company_logo_url=settings.COMPANY_LOGO_URL,
            business_timezone=settings.BUSINESS_TIMEZONE,
            leap_day_policy=settings.LEAP_DAY_POLICY,
            digest_channel_id=settings.DEFAULT_DIGEST_CHANNEL_ID,
            is_active=True,
            is_demo=False,
        )
        db.add(org)
        db.commit()
        db.refresh(org)

    seed_default_templates(db, org.id)
    seed_default_users(db, org.id)
    return org
