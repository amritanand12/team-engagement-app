from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import AuditLog, Organization, User, UserRole
from app.seed import seed_default_organization


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_audit_log_recorded_on_auth_events(db, client):
    seed_default_organization(db)

    # 1. Failed login creates audit log
    fail_resp = client.post(
        "/auth/login",
        json={"email": "nonexistent@test.com", "password": "wrongpassword"},
    )
    assert fail_resp.status_code == 401

    failed_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "LOGIN_FAILED", AuditLog.actor_email == "nonexistent@test.com")
        .first()
    )
    assert failed_log is not None
    assert "invalid" in failed_log.details.lower()

    # 2. Successful login creates audit log
    succ_resp = client.post(
        "/auth/login",
        json={"email": "admin@platform.local", "password": "admin123"},
    )
    assert succ_resp.status_code == 200
    token = succ_resp.json()["access_token"]

    success_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "LOGIN_SUCCESS", AuditLog.actor_email == "admin@platform.local")
        .first()
    )
    assert success_log is not None
    assert success_log.actor_role == "super_admin"

    # 3. Password change creates audit log
    pwd_resp = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "admin123",
            "new_password": "new_admin_password123",
            "confirm_password": "new_admin_password123",
        },
    )
    assert pwd_resp.status_code == 200

    pwd_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "PASSWORD_CHANGED", AuditLog.actor_email == "admin@platform.local")
        .first()
    )
    assert pwd_log is not None
    assert pwd_log.resource_type == "user"


def test_superadmin_can_query_audit_logs(db, client):
    seed_default_organization(db)

    # Login as SuperAdmin
    super_resp = client.post(
        "/auth/login",
        json={"email": "admin@platform.local", "password": "admin123"},
    )
    super_token = super_resp.json()["access_token"]

    # Query audit logs
    logs_resp = client.get(
        "/superadmin/audit-logs",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert logs_resp.status_code == 200
    data = logs_resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["limit"] == 50
    assert data["offset"] == 0

    # Test action filter
    filtered_resp = client.get(
        "/superadmin/audit-logs?action=LOGIN_SUCCESS",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert filtered_resp.status_code == 200
    filtered_data = filtered_resp.json()
    for item in filtered_data["items"]:
        assert item["action"] == "LOGIN_SUCCESS"

    # Test search filter
    search_resp = client.get(
        "/superadmin/audit-logs?search=platform.local",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] >= 1


def test_tenant_admin_strictly_forbidden_from_audit_logs(db, client):
    seed_default_organization(db)

    # 1. Tenant Admin login
    tenant_resp = client.post(
        "/auth/login",
        json={"email": "admin@acme.com", "password": "acme123"},
    )
    assert tenant_resp.status_code == 200
    tenant_token = tenant_resp.json()["access_token"]

    # 2. Tenant Admin attempt to access /superadmin/audit-logs -> 403 Forbidden
    forbidden_resp = client.get(
        "/superadmin/audit-logs",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert forbidden_resp.status_code == 403
    assert "Platform SuperAdmin privileges required" in forbidden_resp.json()["detail"]

    # 3. Unauthenticated attempt -> 401 Unauthorized
    unauth_resp = client.get("/superadmin/audit-logs")
    assert unauth_resp.status_code == 401


def test_superadmin_actions_recorded_in_audit_log(db, client):
    seed_default_organization(db)

    # Login as SuperAdmin
    super_resp = client.post(
        "/auth/login",
        json={"email": "admin@platform.local", "password": "admin123"},
    )
    super_token = super_resp.json()["access_token"]
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # 1. Provision new organization
    prov_resp = client.post(
        "/superadmin/organizations",
        headers=super_headers,
        json={
            "name": "Audit Test Corp",
            "slug": "audit-test-corp",
            "admin_email": "admin@audittest.com",
            "admin_name": "Audit Admin",
            "admin_password": "audittestpass123",
        },
    )
    assert prov_resp.status_code == 201
    new_org = prov_resp.json()

    prov_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "TENANT_PROVISIONED", AuditLog.organization_id == new_org["id"])
        .first()
    )
    assert prov_log is not None
    assert "Audit Test Corp" in prov_log.details

    # 2. Toggle organization status
    toggle_resp = client.patch(
        f"/superadmin/organizations/{new_org['id']}/status?is_active=false",
        headers=super_headers,
    )
    assert toggle_resp.status_code == 200

    toggle_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "TENANT_STATUS_TOGGLED", AuditLog.organization_id == new_org["id"])
        .first()
    )
    assert toggle_log is not None
    assert "suspended" in toggle_log.details

    # 3. SuperAdmin reset tenant password
    reset_resp = client.post(
        f"/superadmin/organizations/{new_org['id']}/reset-password",
        headers=super_headers,
        json={"new_password": "brandnewpassword456"},
    )
    assert reset_resp.status_code == 200

    reset_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "TENANT_PASSWORD_RESET", AuditLog.organization_id == new_org["id"])
        .first()
    )
    assert reset_log is not None
    assert "admin@audittest.com" in reset_log.details
