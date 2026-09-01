"""
Authentication Router.
Provides endpoints for email/password login (SuperAdmin and Tenant Admin),
API key-based authentication, and profile resolution.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Organization, User, UserRole
from app.schemas import ApiKeyLoginIn, AuthResponse, LoginIn, OrganizationOut, UserOut
from app.services.auth import create_access_token, decode_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


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
            # SuperAdmin can optionally specify x-tenant-id to operate on behalf of a tenant
            if x_tenant_id:
                active_org = db.get(Organization, x_tenant_id)
            else:
                active_org = db.query(Organization).filter(Organization.slug == "default").first() or db.query(Organization).first()
        elif user.organization_id:
            active_org = db.get(Organization, user.organization_id)

        return user, active_org

    # 2. API Key Auth
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
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """Logs in using email and password. Distinguishes SuperAdmin from Tenant Admin."""
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    org = None
    if user.organization_id:
        org = db.get(Organization, user.organization_id)
    elif user.role == UserRole.SUPER_ADMIN:
        org = db.query(Organization).filter(Organization.slug == "default").first() or db.query(Organization).first()

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "org_id": org.id if org else None,
    }
    token = create_access_token(token_payload)

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        organization=OrganizationOut.model_validate(org) if org else None,
    )


@router.post("/api-key", response_model=AuthResponse)
def login_with_api_key(payload: ApiKeyLoginIn, db: Session = Depends(get_db)):
    """Instant 1-click login using an Organization API key."""
    key = payload.api_key.strip()
    org = db.query(Organization).filter(Organization.api_key == key, Organization.is_active == True).first()
    if not org and key == settings.ADMIN_API_KEY:
        from app.seed import seed_default_organization
        org = seed_default_organization(db)

    if not org:
        raise HTTPException(status_code=401, detail="Invalid Organization API Key")

    # Find or create virtual user for this tenant
    user = db.query(User).filter(User.organization_id == org.id).first()
    if not user:
        user = User(
            id=f"api-admin-{org.id}",
            email=f"admin@{org.slug}.local",
            full_name=f"{org.name} Admin",
            password_hash="",
            role=UserRole.TENANT_ADMIN,
            organization_id=org.id,
            is_active=True,
        )

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "org_id": org.id,
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        organization=OrganizationOut.model_validate(org),
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
