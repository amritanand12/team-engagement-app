"""
Authentication Router.
Provides endpoints for email/password login (SuperAdmin and Tenant Admin),
API key-based authentication, and profile resolution.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Organization, User, UserRole
from app.schemas import (
    ApiKeyLoginIn,
    AuthResponse,
    ChangePasswordIn,
    ChangePasswordResponse,
    LoginIn,
    OrganizationOut,
    UserOut,
)
from app.services.audit import record_audit_log
from app.services.auth import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

_failed_attempts: dict[str, list[float]] = defaultdict(list)
_rate_limit_lock = threading.Lock()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes
LOCKOUT_DURATION_SECONDS = 60  # 60 seconds cooldown


def check_rate_limit(identifier: str) -> int:
    """Returns seconds remaining if rate limited, or 0 if allowed."""
    if settings.TESTING and not getattr(settings, "FORCE_RATE_LIMIT_TESTING", False):
        return 0
    now = time.time()
    with _rate_limit_lock:
        attempts = [t for t in _failed_attempts.get(identifier, []) if now - t < LOCKOUT_WINDOW_SECONDS]
        _failed_attempts[identifier] = attempts
        if len(attempts) >= MAX_FAILED_ATTEMPTS:
            elapsed = now - attempts[-1]
            if elapsed < LOCKOUT_DURATION_SECONDS:
                return max(1, int(LOCKOUT_DURATION_SECONDS - elapsed))
    return 0


def record_failed_login(identifier: str) -> None:
    now = time.time()
    with _rate_limit_lock:
        _failed_attempts[identifier].append(now)


def clear_failed_login(identifier: str) -> None:
    with _rate_limit_lock:
        _failed_attempts.pop(identifier, None)


def get_current_user_and_org(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> tuple[User, Organization | None]:
    """
    Dependency resolving current user and active organization from JWT Bearer or x-api-key.
    """
    # 1. Bearer Token Auth
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

        user_id = payload.get("sub")
        user = db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User account not found or deactivated")

        # Resolve organization context
        active_org = None
        if user.role == UserRole.SUPER_ADMIN:
            # SuperAdmin can optionally specify x-tenant-id (or slug) to operate on behalf of a tenant
            if x_tenant_id:
                active_org = db.get(Organization, x_tenant_id)
                if not active_org:
                    active_org = db.query(Organization).filter(Organization.slug == x_tenant_id).first()
        elif user.organization_id:
            active_org = db.get(Organization, user.organization_id)

        return user, active_org

    # 2. API Key Auth (for external services / webhooks / tests via x-api-key header)
    if x_api_key:
        org = db.query(Organization).filter(Organization.api_key == x_api_key, Organization.is_active == True).first()
        if not org and x_api_key == settings.ADMIN_API_KEY:
            from app.seed import seed_default_organization
            org = seed_default_organization(db)

        if not org:
            raise HTTPException(status_code=401, detail="Invalid or deactivated Organization API Key")

        # Create virtual tenant admin for API key usage
        virtual_user = User(
            id=f"key-user-{org.id}",
            email=f"admin@{org.slug}.local",
            full_name=f"{org.name} Admin",
            password_hash="",
            role=UserRole.TENANT_ADMIN,
            organization_id=org.id,
            is_active=True,
        )
        return virtual_user, org

    raise HTTPException(status_code=401, detail="Authentication required (Bearer token or x-api-key)")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    """Logs in using email and password. Distinguishes SuperAdmin from Tenant Admin."""
    ip = request.client.host if request.client else None
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    ip = request.client.host if request.client else "unknown"
    email_clean = payload.email.strip().lower()

    # Rate limiting check
    wait_sec = max(check_rate_limit(ip), check_rate_limit(email_clean))
    if wait_sec > 0:
        record_audit_log(
            db,
            action="LOGIN_RATE_LIMITED",
            actor_email=email_clean,
            actor_role="unknown",
            resource_type="auth",
            details=f"Login blocked due to excessive failed attempts ({wait_sec}s cooldown remaining)",
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Please wait {wait_sec} seconds before trying again.",
        )

    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.password_hash):
        record_failed_login(ip)
        record_failed_login(email_clean)
        record_audit_log(
            db,
            action="LOGIN_FAILED",
            actor_email=email_clean,
            actor_role="unknown",
            resource_type="auth",
            details="Failed login attempt - invalid email or password",
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        record_audit_log(
            db,
            action="LOGIN_FAILED",
            actor_email=user.email,
            actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
            actor_id=user.id,
            organization_id=user.organization_id,
            resource_type="auth",
            details="Failed login attempt - account is deactivated",
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Account is deactivated")

    org = None
    if user.organization_id:
        org = db.get(Organization, user.organization_id)
        if org and not org.is_active and user.role != UserRole.SUPER_ADMIN:
            record_audit_log(
                db,
                action="LOGIN_FAILED",
                actor_email=user.email,
                actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                actor_id=user.id,
                organization_id=user.organization_id,
                resource_type="auth",
                details="Failed login attempt - organization is suspended",
                ip_address=ip,
            )
            db.commit()
            raise HTTPException(status_code=403, detail="Organization is suspended")
    # Platform administrators start without a tenant context. They must select an
    # organization before using tenant-scoped endpoints.

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "org_id": org.id if org else None,
    }
    token = create_access_token(token_payload)

    record_audit_log(
        db,
        action="LOGIN_SUCCESS",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=user.organization_id,
        resource_type="auth",
        details="User logged in via email/password",
        ip_address=ip,
    )
    db.commit()

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        organization=OrganizationOut.model_validate(org) if org else None,
    )


@router.post("/api-key", response_model=AuthResponse, deprecated=True)
def login_with_api_key(payload: ApiKeyLoginIn, request: Request, db: Session = Depends(get_db)):
    """
    Deprecated: Interactive web browser logins using Organization API keys have been disabled for production security.
    Please sign in using administrator email and password.
    """
    raise HTTPException(
        status_code=400,
        detail="API Key web login is disabled in production. Please sign in using your administrator email and password.",
    )


@router.get("/me", response_model=AuthResponse)
def get_current_user_profile(
    user_and_org: tuple[User, Organization | None] = Depends(get_current_user_and_org),
):
    """Returns the authenticated user's profile and active organization."""
    user, org = user_and_org
    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "org_id": org.id if org else None,
    })
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        organization=OrganizationOut.model_validate(org) if org else None,
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    payload: ChangePasswordIn,
    request: Request,
    user_and_org: tuple[User, Organization | None] = Depends(get_current_user_and_org),
    db: Session = Depends(get_db),
):
    """
    Updates the authenticated user's password.
    Requires verifying the current password and matching confirmation.
    """
    user, _ = user_and_org
    if not user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be changed for virtual API-key sessions. Please use email/password login.",
        )

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password does not match")

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirmation do not match")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

    db_user = db.get(User, user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User account not found")

    db_user.password_hash = hash_password(payload.new_password)
    record_audit_log(
        db,
        action="PASSWORD_CHANGED",
        actor_email=user.email,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        actor_id=user.id,
        organization_id=user.organization_id,
        resource_type="user",
        resource_id=user.id,
        details="User updated their account password",
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return ChangePasswordResponse(success=True, message="Password successfully updated")
