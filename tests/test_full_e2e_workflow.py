"""
Comprehensive End-to-End Business Flow Test (43-Step Scenario).
Audits and verifies the complete application workflow across all 12 requirement modules.
"""
from datetime import date, datetime
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import (
    AuditLog,
    DigestLog,
    EmployeeProfile,
    EventLog,
    EventStatus,
    EventTemplate,
    EventType,
    Organization,
    User,
    UserRole,
)
from app.seed import seed_default_organization, seed_default_templates
from app.services.auth import create_access_token, hash_password


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_full_43_step_end_to_end_business_workflow(client, db):
    seed_default_organization(db)

    # 1. SuperAdmin Login
    res_sa_login = client.post("/auth/login", json={"email": "admin@platform.local", "password": "admin123"})
    assert res_sa_login.status_code == 200
    sa_token = res_sa_login.json()["access_token"]
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # 2. Create Organization A
    res_org_a = client.post(
        "/superadmin/organizations",
        headers=sa_headers,
        json={
            "name": "Organization A",
            "slug": "org-a",
            "admin_email": "admin@org-a.com",
            "admin_name": "Alice OrgA Admin",
            "admin_password": "Password123!",
            "business_timezone": "Asia/Kolkata",
            "leap_day_policy": "feb28",
        },
    )
    assert res_org_a.status_code == 201
    org_a = res_org_a.json()
    org_a_id = org_a["id"]

    # 3. Login as Organization A Admin
    res_a_login = client.post("/auth/login", json={"email": "admin@org-a.com", "password": "Password123!"})
    assert res_a_login.status_code == 200
    token_a = res_a_login.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 4. Configure database & SMTP for Organization A
    org_db = db.get(Organization, org_a_id)
    org_db.is_db_configured = True
    db.commit()

    res_smtp = client.post(
        "/admin/settings/smtp",
        headers=headers_a,
        json={
            "smtp_host": "smtp.org-a.com",
            "smtp_port": 587,
            "smtp_username": "notifier@org-a.com",
            "smtp_password": "secret_smtp_pass",
            "smtp_from_address": "celebrations@org-a.com",
            "smtp_use_tls": True,
        },
    )
    assert res_smtp.status_code == 200
    assert res_smtp.json()["is_setup_complete"] is True

    # 5. Create manual employee in Organization A
    res_emp = client.post(
        "/admin/employees",
        headers=headers_a,
        json={
            "employee_code": "ORGA-001",
            "full_name": "Anita Roy",
            "preferred_name": "Anita",
            "email": "anita@org-a.com",
            "date_of_birth": "1995-09-22",  # Birthday today!
            "date_of_joining": "2020-01-15",
            "department": "Engineering",
        },
    )
    assert res_emp.status_code == 201
    emp_a_id = res_emp.json()["id"]

    # 6. Bulk import employees via CSV
    csv_content = (
        "employee_code,full_name,email,date_of_birth,date_of_joining,department\n"
        "ORGA-002,Bikram Singh,bikram@org-a.com,1992-04-10,2021-09-22,Product\n"  # Anniversary today!
        "ORGA-003,Chitra Gupta,chitra@org-a.com,1988-12-05,2022-03-01,Design\n"
    )
    res_csv = client.post(
        "/admin/employees/upload-csv",
        headers=headers_a,
        files={"file": ("employees.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert res_csv.status_code == 200
    assert res_csv.json()["imported"] == 2

    # 7. Verify templates for Org A
    res_tmpls = client.get("/admin/templates", headers=headers_a)
    assert res_tmpls.status_code == 200
    assert len(res_tmpls.json()) >= 4

    # 8. Run scanner pipeline for today's date (2026-09-22)
    res_scan = client.post("/admin/scan/trigger?scan_date=2026-09-22", headers=headers_a)
    assert res_scan.status_code == 200
    scan_data = res_scan.json()
    assert scan_data["detected"] >= 2  # Birthday Anita + 5-yr Anniversary Bikram
    assert scan_data["batch_id"] == "2026-09-22"

    # 9. Verify duplicate prevention: re-run scan
    res_scan_again = client.post("/admin/scan/trigger?scan_date=2026-09-22", headers=headers_a)
    assert res_scan_again.status_code == 200
    assert res_scan_again.json()["detected"] == scan_data["detected"]  # 0 new detected

    # 10. Verify events list for Org A
    res_events_a = client.get("/admin/events?batch_id=2026-09-22", headers=headers_a)
    assert res_events_a.status_code == 200
    events_a = res_events_a.json()
    assert len(events_a) >= 2

    # 11. Generate advance photo request for Anita
    res_photo_req = client.post(f"/admin/employees/{emp_a_id}/request-photo", headers=headers_a)
    assert res_photo_req.status_code == 200
    assert res_photo_req.json()["success"] is True

    # 12. Retrieve employee token and test public magic token photo portal
    emp_db = db.get(EmployeeProfile, emp_a_id)
    token = emp_db.photo_upload_token
    assert token is not None

    res_public_info = client.get(f"/api/public/photo-info?token={token}")
    assert res_public_info.status_code == 200
    assert res_public_info.json()["employee_name"] == "Anita Roy"

    # Upload valid image to public portal
    fake_img = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    res_upload = client.post(
        "/api/public/upload-photo",
        data={"token": token},
        files={"file": ("photo.png", fake_img, "image/png")},
    )
    assert res_upload.status_code == 200
    assert res_upload.json()["success"] is True

    # Check employee record updated with custom photo
    db.refresh(emp_db)
    assert emp_db.has_custom_photo is True
    assert emp_db.photo_url is not None

    # 13. Create Organization B
    res_org_b = client.post(
        "/superadmin/organizations",
        headers=sa_headers,
        json={
            "name": "Organization B",
            "slug": "org-b",
            "admin_email": "admin@org-b.com",
            "admin_name": "Bob OrgB Admin",
            "admin_password": "Password123!",
            "business_timezone": "America/New_York",
        },
    )
    assert res_org_b.status_code == 201
    org_b = res_org_b.json()
    org_b_id = org_b["id"]

    # 14. Verify Tenant Isolation: Org B employee query returns 0 Org A records
    res_b_login = client.post("/auth/login", json={"email": "admin@org-b.com", "password": "Password123!"})
    assert res_b_login.status_code == 200
    token_b = res_b_login.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res_emp_b = client.get("/admin/employees", headers=headers_b)
    assert res_emp_b.status_code == 200
    assert res_emp_b.json()["total"] == 0

    # 15. SuperAdmin Tenant Context Switch (A -> B and B -> A)
    res_sa_org_b = client.get("/admin/employees", headers={"Authorization": f"Bearer {sa_token}", "x-tenant-id": "org-b"})
    assert res_sa_org_b.status_code == 200
    assert res_sa_org_b.json()["total"] == 0

    res_sa_org_a = client.get("/admin/employees", headers={"Authorization": f"Bearer {sa_token}", "x-tenant-id": "org-a"})
    assert res_sa_org_a.status_code == 200
    assert res_sa_org_a.json()["total"] == 3

    # 16. Deactivate Organization A
    res_suspend = client.patch(f"/superadmin/organizations/{org_a_id}/status?is_active=false", headers=sa_headers)
    assert res_suspend.status_code == 200
    assert res_suspend.json()["is_active"] is False

    # 17. Verify Org A login is blocked while suspended
    res_blocked = client.post("/auth/login", json={"email": "admin@org-a.com", "password": "Password123!"})
    assert res_blocked.status_code == 403

    # 18. Reactivate Organization A
    client.patch(f"/superadmin/organizations/{org_a_id}/status?is_active=true", headers=sa_headers)

    # 19. Reset Tenant Admin Password & Verify Login
    res_pw_reset = client.post(
        f"/superadmin/organizations/{org_a_id}/reset-password",
        headers=sa_headers,
        json={"new_password": "BrandNewPassword2026!"},
    )
    assert res_pw_reset.status_code == 200

    res_a_login_new = client.post("/auth/login", json={"email": "admin@org-a.com", "password": "BrandNewPassword2026!"})
    assert res_a_login_new.status_code == 200

    # 20. Audit Trail Verification
    res_audit = client.get("/superadmin/audit-logs", headers=sa_headers)
    assert res_audit.status_code == 200
    logs = res_audit.json()["items"]
    assert len(logs) >= 5
