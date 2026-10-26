"""
Public & Webhook Router for Employee Photo Collection.
Handles Google Form webhooks, tokenized employee photo uploads, and public portal queries.
Supports multi-tenant BYODB by searching both the platform DB and dedicated tenant databases.
Enforces a 7-day token expiration policy from the time the request email is dispatched.
"""
from __future__ import annotations

import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import get_db, get_tenant_engine
from app.models import EmployeeProfile, Organization

logger = logging.getLogger("engagement.webhooks")
settings = get_settings()

router = APIRouter(tags=["webhooks"])


@router.get("/upload-photo")
def redirect_to_photo_upload_portal(token: str | None = Query(None)):
    """
    Redirects direct GET requests to /upload-photo on the API server
    to the frontend React upload portal URL.
    """
    base_url = settings.APP_BASE_URL.rstrip("/")
    query_param = f"?token={token}" if token else ""
    return RedirectResponse(url=f"{base_url}/upload-photo{query_param}", status_code=307)

UPLOAD_DIR = Path("uploads/photos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Photo upload tokens expire after 7 days
TOKEN_EXPIRATION_DAYS = 7


class GoogleFormPhotoIn(BaseModel):
    email: EmailStr
    photo_url: str
    employee_code: str | None = None


class PhotoSubmissionResponse(BaseModel):
    success: bool
    message: str
    photo_url: str | None = None
    employee_name: str | None = None


class PublicPhotoInfoResponse(BaseModel):
    employee_name: str
    preferred_name: str | None
    company_name: str
    company_logo_url: str | None
    current_photo_url: str | None
    has_custom_photo: bool
    expires_at: datetime | None = None


def is_token_expired(employee: EmployeeProfile) -> bool:
    """Checks if the photo upload token has passed the 7-day expiration window."""
    if not employee.photo_request_sent_at:
        return False
    return datetime.utcnow() - employee.photo_request_sent_at > timedelta(days=TOKEN_EXPIRATION_DAYS)


def find_employee_by_photo_token(
    token: str, db: Session
) -> tuple[EmployeeProfile | None, Session | None, Organization | None, bool, bool]:
    """
    Finds an employee by their photo upload token in active tenant databases only.

    Returns (employee, active_session, organization, is_tenant_session, is_expired).
    """
    if not token or not token.strip():
        return None, None, None, False, False

    clean_token = token.strip()

    # Employee records are tenant data and are never read from the platform database.
    orgs = (
        db.query(Organization)
        .filter(Organization.is_active.is_(True))
        .all()
    )

    for org in orgs:
        tdb = None
        try:
            eng = get_tenant_engine(org)
            TenantSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)
            tdb = TenantSession()
            emp = tdb.query(EmployeeProfile).filter(EmployeeProfile.photo_upload_token == clean_token).first()
            if emp:
                expired = is_token_expired(emp)
                return emp, tdb, org, True, expired
            tdb.close()
        except Exception as exc:
            logger.warning("Error querying tenant %s for photo token: %s", org.id, exc)
            if tdb:
                try:
                    tdb.close()
                except Exception:
                    pass

    return None, None, None, False, False


def find_employee_by_email_or_code(
    email: str, employee_code: str | None, db: Session
) -> tuple[EmployeeProfile | None, Session | None, Organization | None, bool]:
    """
    Finds an employee by email or code across tenant databases only.
    """
    email_clean = email.strip().lower()
    code_clean = employee_code.strip() if employee_code else None

    orgs = (
        db.query(Organization)
        .filter(Organization.is_active.is_(True))
        .all()
    )

    for org in orgs:
        tdb = None
        try:
            eng = get_tenant_engine(org)
            TenantSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)
            tdb = TenantSession()
            q = tdb.query(EmployeeProfile).filter(EmployeeProfile.email.ilike(email_clean))
            if code_clean:
                q = tdb.query(EmployeeProfile).filter(
                    (EmployeeProfile.email.ilike(email_clean)) | (EmployeeProfile.employee_code == code_clean)
                )
            emp = q.first()
            if emp:
                return emp, tdb, org, True
            tdb.close()
        except Exception as exc:
            logger.warning("Error querying tenant %s by email: %s", org.id, exc)
            if tdb:
                try:
                    tdb.close()
                except Exception:
                    pass

    return None, None, None, False


@router.post("/api/webhooks/google-form-photo", response_model=PhotoSubmissionResponse)
def handle_google_form_webhook(
    payload: GoogleFormPhotoIn,
    db: Session = Depends(get_db),
):
    """
    Receives photo submissions from Google Forms or Google Apps Script webhooks.
    Matches employee across tenant databases by email or employee_code,
    updates photo_url, and sets has_custom_photo = True.
    """
    employee, session, org, is_tenant = find_employee_by_email_or_code(payload.email, payload.employee_code, db)
    if not employee or not session:
        raise HTTPException(
            status_code=404,
            detail=f"No employee found matching email '{payload.email}'",
        )

    try:
        employee.photo_url = payload.photo_url.strip()
        employee.has_custom_photo = True
        session.commit()

        logger.info("Updated custom photo for %s via Google Form webhook", employee.email)
        return PhotoSubmissionResponse(
            success=True,
            message=f"Celebration photo successfully saved for {employee.full_name}!",
            photo_url=employee.photo_url,
            employee_name=employee.full_name,
        )
    finally:
        if is_tenant:
            session.close()


@router.get("/api/public/photo-info", response_model=PublicPhotoInfoResponse)
def get_public_photo_info(
    token: str = Query(..., description="Secure employee photo upload token"),
    db: Session = Depends(get_db),
):
    """
    Retrieves public context for the photo upload portal using a secure token.
    Searches both platform and tenant databases, enforcing a 7-day expiration limit.
    """
    employee, session, org, is_tenant, is_expired = find_employee_by_photo_token(token, db)
    if not employee or not session:
        raise HTTPException(
            status_code=404,
            detail="Invalid photo upload link. Please check the URL or request a new one from your administrator.",
        )

    if is_expired:
        if is_tenant:
            session.close()
        raise HTTPException(
            status_code=410,
            detail="This photo upload link has expired (links are valid for 7 days). Please contact your administrator or HR for a new request link.",
        )

    try:
        company_name = (org.name if org else None) or settings.COMPANY_NAME
        company_logo = (org.company_logo_url if org else None) or settings.COMPANY_LOGO_URL
        expires_at = (
            employee.photo_request_sent_at + timedelta(days=TOKEN_EXPIRATION_DAYS)
            if employee.photo_request_sent_at
            else None
        )

        return PublicPhotoInfoResponse(
            employee_name=employee.full_name,
            preferred_name=employee.preferred_name,
            company_name=company_name,
            company_logo_url=company_logo,
            current_photo_url=employee.photo_url,
            has_custom_photo=employee.has_custom_photo,
            expires_at=expires_at,
        )
    finally:
        if is_tenant:
            session.close()


@router.post("/api/public/upload-photo", response_model=PhotoSubmissionResponse)
async def upload_employee_photo_public(
    token: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Allows employees to directly upload their celebration photo via the secure 1-click upload portal.
    Searches both platform and tenant databases, enforcing a 7-day expiration limit.
    """
    employee, session, org, is_tenant, is_expired = find_employee_by_photo_token(token, db)
    if not employee or not session:
        raise HTTPException(
            status_code=404,
            detail="Invalid photo upload link. Please check the URL or request a new one from your administrator.",
        )

    if is_expired:
        if is_tenant:
            session.close()
        raise HTTPException(
            status_code=410,
            detail="This photo upload link has expired (links are valid for 7 days). Please contact your administrator or HR for a new request link.",
        )

    try:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format '{ext}'. Allowed formats: JPG, PNG, WEBP, GIF",
            )

        # Save to uploads directory
        file_id = uuid.uuid4().hex[:12]
        safe_filename = f"{employee.id}_{file_id}{ext}"
        dest_path = UPLOAD_DIR / safe_filename

        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Store relative path/URL
        public_url = f"/uploads/photos/{safe_filename}"
        employee.photo_url = public_url
        employee.has_custom_photo = True
        session.commit()

        logger.info("Employee %s successfully uploaded celebration photo: %s", employee.email, public_url)
        return PhotoSubmissionResponse(
            success=True,
            message="Your celebration photo has been saved successfully!",
            photo_url=public_url,
            employee_name=employee.preferred_name or employee.full_name,
        )
    finally:
        if is_tenant:
            session.close()
