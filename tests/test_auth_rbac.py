from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import EmployeeProfile, Organization, User, UserRole
from app.seed import seed_default_organization, seed_default_templates
from app.services.auth import hash_password, verify_password


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_password_hashing_and_verification():
    raw = "super_secret_123"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_superadmin_and_tenant_admin_login_flows(db, client):
    org = seed_default_organization(db)

    # 1. SuperAdmin Login
    resp_super = client.post(
        "/auth/login",
        json={"email": "admin@platform.local", "password": "admin123"},
    )
    assert resp_super.status_code == 200
    data_super = resp_super.json()
    assert data_super["user"]["role"] == "super_admin"
    super_token = data_super["access_token"]

    # 2. Tenant Admin Login
    resp_tenant = client.post(
        "/auth/login",
        json={"email": "admin@acme.com", "password": "acme123"},
    )
    assert resp_tenant.status_code == 200
    data_tenant = resp_tenant.json()
    assert data_tenant["user"]["role"] == "tenant_admin"
    assert data_tenant["user"]["organization_id"] == org.id
    tenant_token = data_tenant["access_token"]

    # 3. SuperAdmin can access /superadmin/organizations
    super_orgs = client.get(
        "/superadmin/organizations",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert super_orgs.status_code == 200
    assert len(super_orgs.json()) >= 1

    # 4. Tenant Admin CANNOT access /superadmin/organizations (403 Forbidden)
    forbidden_resp = client.get(
        "/superadmin/organizations",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert forbidden_resp.status_code == 403


def test_superadmin_provisions_new_client_organization(db, client):
    seed_default_organization(db)

    # Login as SuperAdmin
    resp_super = client.post(
        "/auth/login",
        json={"email": "admin@platform.local", "password": "admin123"},
    )
    super_token = resp_super.json()["access_token"]

    # SuperAdmin creates a new tenant "Globex Corp"
    create_payload = {
        "name": "Globex Corporation",
        "slug": "globex",
        "admin_email": "hr@globex.com",
        "admin_name": "Hank Scorpio",
        "admin_password": "scorpio_secret",
        "business_timezone": "America/New_York",
    }
    resp_create = client.post(
        "/superadmin/organizations",
        headers={"Authorization": f"Bearer {super_token}"},
        json=create_payload,
    )
    assert resp_create.status_code == 201
    new_org = resp_create.json()
    assert new_org["name"] == "Globex Corporation"
    assert new_org["slug"] == "globex"

    # New Tenant Admin can now log in
    resp_globex_login = client.post(
        "/auth/login",
        json={"email": "hr@globex.com", "password": "scorpio_secret"},
    )
    assert resp_globex_login.status_code == 200
    globex_data = resp_globex_login.json()
    assert globex_data["user"]["full_name"] == "Hank Scorpio"
    assert globex_data["user"]["organization_id"] == new_org["id"]


def test_superadmin_can_switch_tenant_context(db, client):
    org_a = Organization(name="Org A", slug="orga", api_key="key-a", is_active=True)
    org_b = Organization(name="Org B", slug="orgb", api_key="key-b", is_active=True)
    db.add_all([org_a, org_b])
    db.commit()

    # Add employee to Org B
    emp_b = EmployeeProfile(
        organization_id=org_b.id,
        employee_code="B01",
        full_name="Bob Org B",
        email="bob@orgb.com",
        is_active=True,
    )
    db.add(emp_b)
    db.commit()

    # SuperAdmin login
    seed_default_organization(db)
    resp_super = client.post(
        "/auth/login",
        json={"email": "admin@platform.local", "password": "admin123"},
    )
    super_token = resp_super.json()["access_token"]

    # SuperAdmin switches context to Org B via x-tenant-id header
    resp_b_employees = client.get(
        "/admin/employees",
        headers={
            "Authorization": f"Bearer {super_token}",
            "x-tenant-id": org_b.id,
        },
    )
    assert resp_b_employees.status_code == 200
    items = resp_b_employees.json()["items"]
    assert len(items) == 1
    assert items[0]["full_name"] == "Bob Org B"


def test_tenant_admin_can_change_password(db, client):
    seed_default_organization(db)

    # 1. Login as Tenant Admin
    resp_login = client.post(
        "/auth/login",
        json={"email": "admin@acme.com", "password": "acme123"},
    )
    assert resp_login.status_code == 200
    token = resp_login.json()["access_token"]

    # 2. Change password successfully
    resp_change = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "acme123",
            "new_password": "new_secret_password_2026",
            "confirm_password": "new_secret_password_2026",
        },
    )
    assert resp_change.status_code == 200
    assert resp_change.json()["success"] is True

    # 3. Old password should now fail
    resp_old_login = client.post(
        "/auth/login",
        json={"email": "admin@acme.com", "password": "acme123"},
    )
    assert resp_old_login.status_code == 401

    # 4. New password should succeed
    resp_new_login = client.post(
        "/auth/login",
        json={"email": "admin@acme.com", "password": "new_secret_password_2026"},
    )
    assert resp_new_login.status_code == 200


def test_change_password_validations(db, client):
    seed_default_organization(db)
    resp_login = client.post(
        "/auth/login",
        json={"email": "admin@acme.com", "password": "acme123"},
    )
    token = resp_login.json()["access_token"]

    # Wrong current password
    resp_wrong_cur = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "wrong_current_password",
            "new_password": "valid_new_password_123",
            "confirm_password": "valid_new_password_123",
        },
    )
    assert resp_wrong_cur.status_code == 400
    assert "Current password does not match" in resp_wrong_cur.json()["detail"]

    # Mismatched confirmation
    resp_mismatch = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "acme123",
            "new_password": "valid_new_password_123",
            "confirm_password": "different_confirmation",
        },
    )
    assert resp_mismatch.status_code == 400
    assert "do not match" in resp_mismatch.json()["detail"]

    # Too short (< 8 chars)
    resp_short = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "acme123",
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert resp_short.status_code == 400
    assert "at least 8 characters" in resp_short.json()["detail"]


def test_superadmin_can_reset_tenant_password(db, client):
    org = seed_default_organization(db)

    # SuperAdmin login
    resp_super = client.post(
        "/auth/login",
        json={"email": "admin@platform.local", "password": "admin123"},
    )
    super_token = resp_super.json()["access_token"]

    # SuperAdmin resets password for Acme tenant admin
    resp_reset = client.post(
        f"/superadmin/organizations/{org.id}/reset-password",
        headers={"Authorization": f"Bearer {super_token}"},
        json={"new_password": "super_reset_password_999"},
    )
    assert resp_reset.status_code == 200
    assert resp_reset.json()["success"] is True

    # Tenant admin can now log in with the reset password
    resp_tenant_login = client.post(
        "/auth/login",
        json={"email": "admin@acme.com", "password": "super_reset_password_999"},
    )
    assert resp_tenant_login.status_code == 200

    # Tenant admin CANNOT call superadmin reset-password (403 Forbidden)
    tenant_token = resp_tenant_login.json()["access_token"]
    resp_forbidden = client.post(
        f"/superadmin/organizations/{org.id}/reset-password",
        headers={"Authorization": f"Bearer {tenant_token}"},
        json={"new_password": "hack_attempt_password"},
    )
    assert resp_forbidden.status_code == 403


def test_api_key_web_login_disabled(client):
    """Verifies interactive web login via API key is disabled for production."""
    resp = client.post("/auth/api-key", json={"api_key": "any-key-123"})
    assert resp.status_code == 400
    assert "disabled in production" in resp.json()["detail"]


def test_login_rate_limiting(db, client, monkeypatch):
    """Verifies brute-force protection locks out after 5 consecutive failures."""
    from app.config import get_settings
    from app.routers.auth import _failed_attempts, clear_failed_login
    _failed_attempts.clear()
    s = get_settings()
    monkeypatch.setattr(s, "FORCE_RATE_LIMIT_TESTING", True, raising=False)
    seed_default_organization(db)

    test_ip = "192.168.1.99"
    test_email = "ratelimit_target@acme.com"
    clear_failed_login(test_ip)
    clear_failed_login(test_email)

    # 5 consecutive failed attempts
    for _ in range(5):
        fail_resp = client.post(
            "/auth/login",
            headers={"x-forwarded-for": test_ip},
            json={"email": test_email, "password": "wrong_password"},
        )
        assert fail_resp.status_code == 401

    # 6th attempt should be blocked with 429 Too Many Requests
    blocked_resp = client.post(
        "/auth/login",
        headers={"x-forwarded-for": test_ip},
        json={"email": test_email, "password": "wrong_password"},
    )
    assert blocked_resp.status_code == 429
    assert "Too many failed login attempts" in blocked_resp.json()["detail"]

    # Clean up rate limit state for subsequent tests
    clear_failed_login(test_ip)
    clear_failed_login(test_email)
    clear_failed_login("testclient")
