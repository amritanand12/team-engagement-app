from __future__ import annotations

import io
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import EmployeeProfile, Organization, EventLog
from app.services.photo_requester import (
    ensure_photo_token,
    get_photo_submission_link,
    render_photo_request_email,
    send_single_photo_request,
    scan_and_send_advance_photo_requests,
)


@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_ensure_photo_token(db, default_org, employee_factory):
    emp = employee_factory(code="P001", name="Dev Test", email="dev@example.com")
    assert emp.photo_upload_token is None

    token = ensure_photo_token(emp)
    assert token is not None
    assert len(token) >= 32
    assert emp.photo_upload_token == token

    # Idempotent
    token2 = ensure_photo_token(emp)
    assert token2 == token


def test_photo_submission_link(db, default_org, employee_factory):
    emp = employee_factory(code="P002", name="Dev Link", email="devlink@example.com")
    
    # Default without custom Google Form URL uses portal
    default_org.google_form_url = None
    link = get_photo_submission_link(emp, default_org)
    assert "/upload-photo?token=" in link
    assert emp.photo_upload_token in link

    # With Google Form URL configured
    default_org.google_form_url = "https://forms.gle/xyz123"
    custom_link = get_photo_submission_link(emp, default_org)
    assert custom_link == "https://forms.gle/xyz123"


def test_render_photo_request_email(db, default_org, employee_factory):
    emp = employee_factory(code="P003", name="Rohan Sharma", email="rohan@example.com")
    subj, html = render_photo_request_email(
        employee=emp,
        org=default_org,
        event_label="Birthday",
        celebration_date=date.today() + timedelta(days=7),
    )
    assert "Birthday" in subj
    assert "Rohan" in html
    assert "photo" in html.lower()


def test_scan_and_send_advance_photo_requests(db, default_org, employee_factory):
    scan_date = date(2026, 5, 10)
    # Employee with birthday exactly 7 days ahead (May 17)
    emp_target = employee_factory(
        code="P004",
        name="Upcoming Star",
        email="star@example.com",
        dob=date(1995, 5, 17),
    )
    # Employee with birthday not 7 days ahead
    emp_other = employee_factory(
        code="P005",
        name="Far Away",
        email="far@example.com",
        dob=date(1995, 8, 20),
    )

    results = scan_and_send_advance_photo_requests(
        db, organization_id=default_org.id, scan_date=scan_date
    )
    assert len(results) == 1
    assert results[0]["employee_id"] == emp_target.id
    assert results[0]["status"] == "sent"

    db.refresh(emp_target)
    assert emp_target.photo_request_sent_at is not None


def test_webhooks_google_form_submission(client, db, default_org, employee_factory):
    emp = employee_factory(code="P006", name="Form Submitter", email="form@example.com")
    assert emp.has_custom_photo is False

    resp = client.post(
        "/api/webhooks/google-form-photo",
        json={
            "email": "form@example.com",
            "photo_url": "https://storage.googleapis.com/test-bucket/my_photo.jpg",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    db.refresh(emp)
    assert emp.has_custom_photo is True
    assert emp.photo_url == "https://storage.googleapis.com/test-bucket/my_photo.jpg"


def test_public_upload_portal_flow(client, db, default_org, employee_factory):
    emp = employee_factory(code="P007", name="Portal User", email="portal@example.com")
    token = ensure_photo_token(emp)
    db.commit()

    # 1. Info endpoint
    info_resp = client.get(f"/api/public/photo-info?token={token}")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["employee_name"] == "Portal User"

    # 2. Upload file endpoint
    fake_img = io.BytesIO(b"fake-image-bytes-data")
    upload_resp = client.post(
        "/api/public/upload-photo",
        data={"token": token},
        files={"file": ("selfie.jpg", fake_img, "image/jpeg")},
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["success"] is True
    assert "/uploads/photos/" in upload_data["photo_url"]

    db.refresh(emp)
    assert emp.has_custom_photo is True
    assert "/uploads/photos/" in emp.photo_url


def test_token_expires_after_7_days(client, db, default_org, employee_factory):
    from datetime import datetime
    emp = employee_factory(code="P008", name="Expiring User", email="expiring@example.com")
    token = ensure_photo_token(emp)
    # Set request sent at 8 days ago
    emp.photo_request_sent_at = datetime.utcnow() - timedelta(days=8)
    db.commit()

    # Info endpoint returns 410 Gone with expired message
    info_resp = client.get(f"/api/public/photo-info?token={token}")
    assert info_resp.status_code == 410
    assert "expired" in info_resp.json()["detail"].lower()

    # Upload endpoint also returns 410 Gone with expired message
    fake_img = io.BytesIO(b"fake-image-bytes-data")
    upload_resp = client.post(
        "/api/public/upload-photo",
        data={"token": token},
        files={"file": ("selfie.jpg", fake_img, "image/jpeg")},
    )
    assert upload_resp.status_code == 410
    assert "expired" in upload_resp.json()["detail"].lower()


