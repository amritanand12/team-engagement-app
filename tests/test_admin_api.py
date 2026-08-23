from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"x-api-key": "test-key"}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_admin_endpoint_requires_api_key(client):
    resp = client.post("/admin/scan/trigger")
    assert resp.status_code == 422  # missing required header


def test_admin_endpoint_rejects_wrong_api_key(client):
    resp = client.post("/admin/scan/trigger", headers={"x-api-key": "wrong"})
    assert resp.status_code == 401


def test_admin_trigger_scan_with_valid_key(client):
    resp = client.post(
        "/admin/scan/trigger", headers=HEADERS, params={"scan_date": "2026-08-22"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["batch_id"] == "2026-08-22"
    assert "digest_status" in body


def test_admin_trigger_scan_is_idempotent_over_http(client):
    resp1 = client.post("/admin/scan/trigger", headers=HEADERS, params={"scan_date": "2026-09-01"})
    resp2 = client.post("/admin/scan/trigger", headers=HEADERS, params={"scan_date": "2026-09-01"})
    assert resp1.status_code == 200 and resp2.status_code == 200
    assert resp2.json()["detected"] == resp1.json()["detected"]


def test_admin_list_events_with_valid_key(client):
    client.post("/admin/scan/trigger", headers=HEADERS, params={"scan_date": "2026-08-22"})
    resp = client.get("/admin/events", headers=HEADERS)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_admin_get_nonexistent_event_returns_404(client):
    resp = client.get("/admin/events/does-not-exist", headers=HEADERS)
    assert resp.status_code == 404


def test_admin_get_nonexistent_digest_returns_404(client):
    resp = client.get("/admin/digests/2099-01-01", headers=HEADERS)
    assert resp.status_code == 404


def test_admin_resend_refuses_already_sent_event(client):
    trigger = client.post(
        "/admin/scan/trigger", headers=HEADERS, params={"scan_date": "2026-10-05"}
    ).json()
    events = client.get(
        "/admin/events", headers=HEADERS, params={"batch_id": trigger["batch_id"]}
    ).json()
    if not events:
        pytest.skip("No events landed on this synthetic date in the seeded fixture")
    sent_event = next((e for e in events if e["status"] == "sent"), None)
    if not sent_event:
        pytest.skip("No sent event available to test resend-refusal against")

    resend_resp = client.post(f"/admin/events/{sent_event['id']}/resend", headers=HEADERS)
    assert resend_resp.status_code == 200
    assert "Already sent" in resend_resp.json()["message"]


def test_admin_resend_nonexistent_event_404(client):
    resp = client.post("/admin/events/does-not-exist/resend", headers=HEADERS)
    assert resp.status_code == 404


def test_admin_digest_lookup_after_trigger(client):
    trigger = client.post(
        "/admin/scan/trigger", headers=HEADERS, params={"scan_date": "2026-11-11"}
    ).json()
    resp = client.get(f"/admin/digests/{trigger['batch_id']}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["batch_id"] == trigger["batch_id"]


# ---------------------------------------------------------------------------
# Employee Management Endpoints
# ---------------------------------------------------------------------------


def test_admin_create_and_get_employee(client):
    payload = {
        "employee_code": "TEST-EMP-001",
        "full_name": "Test User",
        "preferred_name": "Tester",
        "email": "test.user@example.com",
        "photo_url": "https://example.com/photo.jpg",
        "date_of_birth": "1990-05-15",
        "date_of_joining": "2020-06-01",
        "department": "Engineering",
        "is_active": True,
    }
    resp = client.post("/admin/employees", headers=HEADERS, json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["employee_code"] == "TEST-EMP-001"
    assert created["full_name"] == "Test User"
    assert created["email"] == "test.user@example.com"
    emp_id = created["id"]

    # Get employee detail
    detail_resp = client.get(f"/admin/employees/{emp_id}", headers=HEADERS)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == emp_id
    assert "recent_events" in detail


def test_admin_create_employee_duplicate_code_fails(client):
    payload = {
        "employee_code": "DUP-001",
        "full_name": "Duplicate User 1",
        "email": "dup1@example.com",
    }
    resp1 = client.post("/admin/employees", headers=HEADERS, json=payload)
    assert resp1.status_code == 201

    payload2 = {
        "employee_code": "DUP-001",
        "full_name": "Duplicate User 2",
        "email": "dup2@example.com",
    }
    resp2 = client.post("/admin/employees", headers=HEADERS, json=payload2)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_admin_create_employee_invalid_email_fails(client):
    payload = {
        "employee_code": "INV-EMAIL-001",
        "full_name": "Invalid Email",
        "email": "not-an-email",
    }
    resp = client.post("/admin/employees", headers=HEADERS, json=payload)
    assert resp.status_code == 422


def test_admin_patch_employee(client):
    payload = {
        "employee_code": "PATCH-001",
        "full_name": "Patch User",
        "email": "patch@example.com",
    }
    create_resp = client.post("/admin/employees", headers=HEADERS, json=payload)
    assert create_resp.status_code == 201
    emp_id = create_resp.json()["id"]

    # Patch preferred name and department
    patch_resp = client.patch(
        f"/admin/employees/{emp_id}",
        headers=HEADERS,
        json={"preferred_name": "Patty", "department": "Marketing", "is_active": False},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["preferred_name"] == "Patty"
    assert updated["department"] == "Marketing"
    assert updated["is_active"] is False


def test_admin_list_employees_pagination_and_search(client):
    resp = client.get("/admin/employees", headers=HEADERS, params={"search": "Patch", "limit": 10, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["limit"] == 10
    assert data["offset"] == 0


# ---------------------------------------------------------------------------
# Templates Endpoints
# ---------------------------------------------------------------------------


def test_admin_list_and_patch_templates(client):
    resp = client.get("/admin/templates", headers=HEADERS)
    assert resp.status_code == 200
    templates = resp.json()
    assert len(templates) >= 4

    first_tmpl = templates[0]
    tmpl_id = first_tmpl["id"]
    curr_active = first_tmpl["is_active"]

    # Toggle active
    patch_resp = client.patch(
        f"/admin/templates/{tmpl_id}",
        headers=HEADERS,
        json={"is_active": not curr_active},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is (not curr_active)

    # Revert back
    client.patch(
        f"/admin/templates/{tmpl_id}",
        headers=HEADERS,
        json={"is_active": curr_active},
    )


# ---------------------------------------------------------------------------
# Stats Summary & Digest Listing & HRMS Sync Endpoints
# ---------------------------------------------------------------------------


def test_admin_get_stats_summary(client):
    resp = client.get("/admin/stats/summary", headers=HEADERS, params={"days": 7})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_employees" in data
    assert "active_employees" in data
    assert "inactive_employees" in data
    assert "today_stats" in data
    assert "upcoming_events_7d" in data
    assert "daily_stats" in data
    assert len(data["daily_stats"]) == 7


def test_admin_trigger_hrms_sync(client):
    resp = client.post("/admin/hrms-sync/trigger", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "created" in data
    assert "updated" in data
    assert "message" in data


def test_admin_list_digests(client):
    # Trigger a scan first
    client.post("/admin/scan/trigger", headers=HEADERS, params={"scan_date": "2026-12-01"})
    resp = client.get("/admin/digests", headers=HEADERS, params={"limit": 10, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["limit"] == 10

