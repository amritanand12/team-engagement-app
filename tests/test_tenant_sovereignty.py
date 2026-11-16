from __future__ import annotations

import uuid
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, provision_tenant_database
from app.main import app
from app.models import EmployeeProfile, EventTemplate, Organization, User, UserRole
from app.services.crypto import decrypt_credential, encrypt_credential


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_credential_encryption_roundtrip():
    secret = "SuperSecretPostgresPassword#2026!"
    ciphertext = encrypt_credential(secret)
    assert ciphertext != secret
    assert ciphertext.startswith("enc:v1:")

    plaintext = decrypt_credential(ciphertext)
    assert plaintext == secret

    # None and invalid handling
    assert decrypt_credential(None) is None
    assert not decrypt_credential("")
    assert decrypt_credential("not_encrypted") == "not_encrypted"


def test_onboarding_guard_blocks_unconfigured_tenant(client, db):
    """
    Ensures an unconfigured tenant cannot insert employee data, upload CSV, or trigger scans,
    returning HTTP 403 with the exact required warning message.
    """
    org_id = str(uuid.uuid4())
    api_key = f"key-{uuid.uuid4().hex[:8]}"

    unconfigured_org = Organization(
        id=org_id,
        name="Privacy First Corp",
        slug=f"privacy-corp-{uuid.uuid4().hex[:6]}",
        api_key=api_key,
        is_active=True,
        is_demo=False,
        is_setup_complete=False,
        is_db_configured=False,
        is_smtp_configured=False,
    )
    db.add(unconfigured_org)
    db.commit()

    headers = {"x-api-key": api_key}
    expected_warning = "You cannot add your data before you configure your database and email provider service."

    # 1. Block create employee
    emp_resp = client.post(
        "/admin/employees",
        headers=headers,
        json={
            "employee_code": "P001",
            "full_name": "Alice Privacy",
            "email": "alice@privacy.corp",
            "department": "Engineering",
        },
    )
    assert emp_resp.status_code == 403
    assert emp_resp.json()["detail"] == expected_warning

    # 2. Block CSV upload
    csv_resp = client.post(
        "/admin/employees/upload-csv",
        headers=headers,
        files={"file": ("employees.csv", b"employee_code,full_name,email\nP001,Alice,alice@corp.com", "text/csv")},
    )
    assert csv_resp.status_code == 403
    assert csv_resp.json()["detail"] == expected_warning

    # 3. Block Scan Trigger
    scan_resp = client.post("/admin/scan/trigger", headers=headers)
    assert scan_resp.status_code == 403
    assert scan_resp.json()["detail"] == expected_warning

    # 4. Block HRMS Sync
    sync_resp = client.post("/admin/hrms-sync/trigger", headers=headers)
    assert sync_resp.status_code == 403
    assert sync_resp.json()["detail"] == expected_warning


def test_save_smtp_configuration_activates_smtp(client, db):
    """
    Tests saving SMTP settings updates the organization and marks is_smtp_configured = True.
    """
    org_id = str(uuid.uuid4())
    api_key = f"key-{uuid.uuid4().hex[:8]}"

    org = Organization(
        id=org_id,
        name="Acme Communications",
        slug=f"acme-comm-{uuid.uuid4().hex[:6]}",
        api_key=api_key,
        is_active=True,
        is_demo=False,
        is_setup_complete=False,
        is_db_configured=False,
        is_smtp_configured=False,
    )
    db.add(org)
    db.commit()

    headers = {"x-api-key": api_key}

    # Save SMTP config
    resp = client.post(
        "/admin/settings/smtp",
        headers=headers,
        json={
            "smtp_host": "smtp.mailgun.org",
            "smtp_port": 587,
            "smtp_username": "postmaster@acme.com",
            "smtp_password": "smtp_secret_pass",
            "smtp_from_address": "celebrations@acme.com",
            "smtp_use_tls": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_smtp_configured"] is True
    assert data["is_setup_complete"] is False  # DB still pending
    assert data["smtp_host"] == "smtp.mailgun.org"
    assert "smtp_password" not in data  # password not exposed

    # Verify password was encrypted in database
    db.refresh(org)
    assert org.is_smtp_configured is True
    assert org.smtp_password.startswith("enc:v1:")
    assert decrypt_credential(org.smtp_password) == "smtp_secret_pass"


def test_test_smtp_connection_endpoint(client, default_org):
    """
    Tests test-smtp endpoint with mock mailer provider.
    """
    headers = {"x-api-key": default_org.api_key}
    resp = client.post(
        "/admin/settings/test-smtp",
        headers=headers,
        json={
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_from_address": "test@test.com",
            "test_recipient": "admin@test.com",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "successfully sent" in data["message"]


def test_provision_tenant_database_and_unlock_onboarding(client, db):
    """
    Verifies that provision_tenant_database sets up all tables and default templates in a dedicated engine,
    and once both DB and SMTP are configured, the onboarding guard unlocks data insertion.
    """
    org_id = str(uuid.uuid4())
    api_key = f"key-{uuid.uuid4().hex[:8]}"

    org = Organization(
        id=org_id,
        name="Sovereign Enterprise",
        slug=f"sovereign-{uuid.uuid4().hex[:6]}",
        api_key=api_key,
        is_active=True,
        is_demo=False,
        is_setup_complete=False,
        is_db_configured=False,
        is_smtp_configured=True,  # SMTP already configured
    )
    db.add(org)
    db.commit()

    # Create dedicated tenant engine (simulating tenant dedicated DB)
    dedicated_engine = create_engine("sqlite://")
    success, msg = provision_tenant_database(org, target_engine=dedicated_engine)
    assert success is True

    # Verify tables exist and templates were seeded in the dedicated engine
    DedicatedSession = sessionmaker(bind=dedicated_engine)
    with DedicatedSession() as s:
        templates = s.query(EventTemplate).filter(EventTemplate.organization_id == org_id).all()
        assert len(templates) == 4
        mirror_org = s.get(Organization, org_id)
        assert mirror_org is not None
        assert mirror_org.name == "Sovereign Enterprise"

    # Now mark DB configured and setup complete
    org.is_db_configured = True
    org.is_setup_complete = True
    db.commit()

    headers = {"x-api-key": api_key}

    # Onboarding guard is now UNLOCKED!
    emp_resp = client.post(
        "/admin/employees",
        headers=headers,
        json={
            "employee_code": "SE-001",
            "full_name": "Elena Rostova",
            "email": "elena@sovereign.corp",
            "department": "Security & Compliance",
        },
    )
    assert emp_resp.status_code == 201
    emp_data = emp_resp.json()
    assert emp_data["employee_code"] == "SE-001"
    assert emp_data["full_name"] == "Elena Rostova"

    # Telemetry cached employee count on platform org was updated
    db.refresh(org)
    assert org.cached_employee_count >= 1

    dedicated_engine.dispose()
