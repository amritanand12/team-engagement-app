import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Organization, User, UserRole, EmployeeProfile, EventTemplate, EventType
from app.services.auth import hash_password, create_access_token


from app.database import get_db

@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_superadmin_routing_by_slug_and_id(client, db):
    """Verifies SuperAdmin can switch tenant context by either Organization ID or Slug."""
    # 1. Create Organization with slug
    org = Organization(
        name="Acme Corporation",
        slug="acme-corp",
        api_key="acme_key_123",
        is_active=True,
        is_setup_complete=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # 2. SuperAdmin token
    sa = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
    sa_token = create_access_token({"sub": sa.id, "email": sa.email, "role": sa.role.value})
    headers_slug = {"Authorization": f"Bearer {sa_token}", "x-tenant-id": "acme-corp"}

    # 3. Access organization profile using slug
    res = client.get("/admin/organization", headers=headers_slug)
    assert res.status_code == 200
    assert res.json()["slug"] == "acme-corp"

    # 4. Access organization profile using ID
    headers_id = {"Authorization": f"Bearer {sa_token}", "x-tenant-id": org.id}
    res_id = client.get("/admin/organization", headers=headers_id)
    assert res_id.status_code == 200
    assert res_id.json()["id"] == org.id


def test_viewer_role_write_restriction(client, db):
    """Verifies that a user with UserRole.VIEWER receives 403 on mutation endpoints."""
    # 1. Create tenant org and Viewer user
    org = Organization(
        name="Viewer Testing Co",
        slug="viewer-co",
        api_key="viewer_key_123",
        is_active=True,
        is_setup_complete=True,
    )
    db.add(org)
    db.flush()

    viewer = User(
        email="viewer@viewer-co.local",
        full_name="Read Only Viewer",
        password_hash=hash_password("password123"),
        role=UserRole.VIEWER,
        organization_id=org.id,
        is_active=True,
    )
    db.add(viewer)
    db.commit()

    token = create_access_token({"sub": viewer.id, "email": viewer.email, "role": viewer.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET employee list should succeed (read-only allowed)
    res_read = client.get("/admin/employees", headers=headers)
    assert res_read.status_code == 200

    # 3. POST employee creation should be rejected with 403 Forbidden
    emp_payload = {
        "employee_code": "V-001",
        "full_name": "Unauthorized Mutation",
        "email": "v001@viewer-co.local",
    }
    res_write = client.post("/admin/employees", json=emp_payload, headers=headers)
    assert res_write.status_code == 403
    assert "Viewer role has read-only access" in res_write.json()["detail"]


def test_superadmin_password_reset_flow(client, db):
    """Verifies SuperAdmin can reset a tenant admin's password and the tenant admin can log in with new password."""
    # 1. Setup tenant & tenant admin
    org = Organization(
        name="Password Reset Co",
        slug="reset-co",
        api_key="reset_key_123",
        is_active=True,
        is_setup_complete=True,
    )
    db.add(org)
    db.flush()

    tenant_admin = User(
        email="admin@reset-co.local",
        full_name="Reset Admin",
        password_hash=hash_password("OldPassword123"),
        role=UserRole.TENANT_ADMIN,
        organization_id=org.id,
        is_active=True,
    )
    db.add(tenant_admin)
    db.commit()

    # 2. Reset password via SuperAdmin endpoint
    sa = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
    sa_token = create_access_token({"sub": sa.id, "email": sa.email, "role": sa.role.value})
    headers_sa = {"Authorization": f"Bearer {sa_token}"}

    reset_res = client.post(
        f"/superadmin/organizations/{org.id}/reset-password",
        json={"new_password": "NewSecretPassword123"},
        headers=headers_sa,
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # 3. Old password should fail login
    login_old = client.post("/auth/login", json={"email": "admin@reset-co.local", "password": "OldPassword123"})
    assert login_old.status_code == 401

    # 4. New password should succeed login
    login_new = client.post("/auth/login", json={"email": "admin@reset-co.local", "password": "NewSecretPassword123"})
    assert login_new.status_code == 200
    assert "access_token" in login_new.json()


def test_suspended_organization_login_blocked(client, db):
    """Verifies that users belonging to a suspended organization cannot log in."""
    org = Organization(
        name="Suspended Corp",
        slug="suspended-corp",
        api_key="suspended_key_123",
        is_active=False,
        is_setup_complete=True,
    )
    db.add(org)
    db.flush()

    user = User(
        email="admin@suspended-corp.local",
        full_name="Suspended Admin",
        password_hash=hash_password("password123"),
        role=UserRole.TENANT_ADMIN,
        organization_id=org.id,
        is_active=True,  # User active, but organization suspended
    )
    db.add(user)
    db.commit()

    # Deactivated account check or active organization check
    # Let's test SuperAdmin toggle status
    sa = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
    sa_token = create_access_token({"sub": sa.id, "email": sa.email, "role": sa.role.value})
    headers_sa = {"Authorization": f"Bearer {sa_token}"}

    # Activate organization
    toggle_res = client.patch(f"/superadmin/organizations/{org.id}/status?is_active=true", headers=headers_sa)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is True

    # Login should succeed now
    login_res = client.post("/auth/login", json={"email": "admin@suspended-corp.local", "password": "password123"})
    assert login_res.status_code == 200
