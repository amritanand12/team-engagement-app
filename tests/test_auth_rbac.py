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
