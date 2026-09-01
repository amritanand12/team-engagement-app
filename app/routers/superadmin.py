"""
Platform SuperAdmin Router.
Provides platform-level management endpoints exclusively accessible by SuperAdmins
to provision client organizations, manage tenant accounts, and monitor platform health.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EmployeeProfile, EventLog, Organization, User, UserRole
from app.routers.auth import get_current_user_and_org
from app.schemas import CreateTenantIn, OrganizationOut, SuperAdminOrgOut, UserOut
from app.seed import seed_default_templates
from app.services.auth import hash_password

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


def require_superadmin(
    user_and_org: tuple[User, Organization | None] = Depends(get_current_user_and_org),
) -> User:
    user, _ = user_and_org
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403, detail="Forbidden: Platform SuperAdmin privileges required"
        )
    return user


@router.get("/organizations", response_model=list[SuperAdminOrgOut])
def list_all_organizations(
    _: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Lists all client organizations across the entire platform with stats."""
    orgs = db.query(Organization).order_by(Organization.created_at.desc()).all()
    results: list[SuperAdminOrgOut] = []

    for org in orgs:
        emp_count = db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id).count()
        event_count = db.query(EventLog).filter(EventLog.organization_id == org.id).count()
        results.append(
            SuperAdminOrgOut(
                id=org.id,
                name=org.name,
                slug=org.slug,
                api_key=org.api_key,
                company_logo_url=org.company_logo_url,
                business_timezone=org.business_timezone,
                is_active=org.is_active,
                is_demo=org.is_demo,
                employee_count=emp_count,
                event_count=event_count,
                created_at=org.created_at,
            )
        )
    return results


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization_and_admin(
    payload: CreateTenantIn,
    _: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Provisions a new client organization and creates its initial Tenant Admin."""
    slug = payload.slug or payload.name.lower().replace(" ", "-").replace(".", "")
    existing_org = db.query(Organization).filter(Organization.slug == slug).first()
    if existing_org:
        raise HTTPException(status_code=400, detail=f"Organization with slug '{slug}' already exists")

    existing_user = db.query(User).filter(User.email == payload.admin_email.strip().lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail=f"User with email '{payload.admin_email}' already exists")

    # 1. Create Organization
    org = Organization(
        id=str(uuid.uuid4()),
        name=payload.name,
        slug=slug,
        api_key=f"org_{uuid.uuid4().hex[:24]}",
        business_timezone=payload.business_timezone,
        leap_day_policy=payload.leap_day_policy,
        is_active=True,
        is_demo=False,
    )
    db.add(org)
    db.flush()

    # 2. Seed Default Templates for this new tenant
    seed_default_templates(db, org.id)

    # 3. Create Tenant Admin User
    admin_user = User(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        email=payload.admin_email.strip().lower(),
        full_name=payload.admin_name,
        password_hash=hash_password(payload.admin_password),
        role=UserRole.TENANT_ADMIN,
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(org)

    return org


@router.patch("/organizations/{org_id}/status", response_model=OrganizationOut)
def toggle_organization_status(
    org_id: str,
    is_active: bool = Query(...),
    _: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Suspends or reactivates a client organization."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = is_active
    db.commit()
    db.refresh(org)
    return org
