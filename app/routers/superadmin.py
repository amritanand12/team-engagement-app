"""
Platform SuperAdmin Router.
Provides platform-level management endpoints exclusively accessible by SuperAdmins
to provision client organizations, manage tenant accounts, and monitor platform health.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, EmployeeProfile, EventLog, Organization, User, UserRole
from app.routers.auth import get_current_user_and_org
from app.schemas import (
    AuditLogOut,
    ChangePasswordResponse,
    CreateTenantIn,
    OrganizationOut,
    PaginatedAuditLogsOut,
    ResetPasswordIn,
    SuperAdminOrgOut,
    UserOut,
)
from app.seed import seed_default_templates
from app.services.audit import record_audit_log
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
    request: Request,
    current_user: User = Depends(require_superadmin),
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

    record_audit_log(
        db,
        action="TENANT_PROVISIONED",
        actor_email=current_user.email,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        actor_id=current_user.id,
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        details=f"Provisioned organization '{org.name}' ({org.slug}) with admin {admin_user.email}",
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(org)

    return org


@router.patch("/organizations/{org_id}/status", response_model=OrganizationOut)
def toggle_organization_status(
    org_id: str,
    request: Request,
    is_active: bool = Query(...),
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Suspends or reactivates a client organization."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = is_active
    record_audit_log(
        db,
        action="TENANT_STATUS_TOGGLED",
        actor_email=current_user.email,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        actor_id=current_user.id,
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        details=f"Changed status of organization '{org.name}' to {'active' if is_active else 'suspended'}",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(org)
    return org


@router.post("/organizations/{org_id}/reset-password", response_model=ChangePasswordResponse)
def reset_tenant_admin_password(
    org_id: str,
    payload: ResetPasswordIn,
    request: Request,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Platform SuperAdmin capability to reset the password of an organization's tenant admin."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

    admin_user = (
        db.query(User)
        .filter(User.organization_id == org.id, User.role == UserRole.TENANT_ADMIN)
        .first()
    )
    if not admin_user:
        raise HTTPException(status_code=404, detail="Tenant administrator account not found for this organization")

    admin_user.password_hash = hash_password(payload.new_password)
    record_audit_log(
        db,
        action="TENANT_PASSWORD_RESET",
        actor_email=current_user.email,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        actor_id=current_user.id,
        organization_id=org.id,
        resource_type="user",
        resource_id=admin_user.id,
        details=f"SuperAdmin reset password for tenant admin '{admin_user.email}' (org: {org.name})",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return ChangePasswordResponse(
        success=True,
        message=f"Password for {admin_user.email} successfully updated",
    )


@router.delete("/organizations/{org_id}", response_model=ChangePasswordResponse)
def delete_organization(
    org_id: str,
    request: Request,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Permanently deletes a client organization and cascades all associated data."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_name = org.name
    record_audit_log(
        db,
        action="TENANT_DELETED",
        actor_email=current_user.email,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        actor_id=current_user.id,
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        details=f"SuperAdmin permanently deleted organization '{org_name}' ({org.slug})",
        ip_address=request.client.host if request.client else None,
    )
    db.delete(org)
    db.commit()

    return ChangePasswordResponse(
        success=True,
        message=f"Organization '{org_name}' and all associated records permanently deleted",
    )


@router.get("/audit-logs", response_model=PaginatedAuditLogsOut)
def list_audit_logs(
    _: User = Depends(require_superadmin),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieves system-wide audit logs with filtering and pagination. SuperAdmin only."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (AuditLog.actor_email.ilike(term))
            | (AuditLog.details.ilike(term))
            | (AuditLog.action.ilike(term))
            | (AuditLog.resource_type.ilike(term))
        )
    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PaginatedAuditLogsOut(
        items=[AuditLogOut.model_validate(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )
