from __future__ import annotations

from datetime import date
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import EmployeeProfile, EventLog, EventStatus, EventTemplate, EventType
from app.services.renderer import render_event
from tests.conftest import make_employee

HEADERS = {"x-api-key": "test-key"}


@pytest.fixture()
def client(db):
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_and_list_custom_templates(client):
    create_resp = client.post(
        "/admin/templates",
        headers=HEADERS,
        json={
            "name": "Pastel Confetti Birthday",
            "event_type": "birthday",
            "subject_line": "✨ Wishing you joy, {{ name }}!",
            "html_body": "<div>Happy Birthday {{ name }} at {{ company_name }}!</div>",
            "is_default": False,
            "is_active": True,
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == "Pastel Confetti Birthday"
    assert created["event_type"] == "birthday"
    assert created["is_default"] is False
    assert created["is_active"] is True
    assert "id" in created

    list_resp = client.get("/admin/templates", headers=HEADERS)
    assert list_resp.status_code == 200
    templates = list_resp.json()
    names = [t["name"] for t in templates]
    assert "Pastel Confetti Birthday" in names


def test_set_default_template_switches_defaults(client):
    r1 = client.post(
        "/admin/templates",
        headers=HEADERS,
        json={
            "name": "Design Alpha",
            "event_type": "birthday",
            "subject_line": "Happy Birthday {{ name }}!",
            "html_body": "<h1>Alpha {{ name }}</h1>",
            "is_default": True,
        },
    )
    assert r1.status_code == 201
    alpha_id = r1.json()["id"]

    list_resp = client.get("/admin/templates", headers=HEADERS)
    alpha = next(t for t in list_resp.json() if t["id"] == alpha_id)
    assert alpha["is_default"] is True

    r2 = client.post(
        "/admin/templates",
        headers=HEADERS,
        json={
            "name": "Design Beta",
            "event_type": "birthday",
            "subject_line": "Beta Birthday {{ name }}!",
            "html_body": "<h1>Beta {{ name }}</h1>",
            "is_default": True,
        },
    )
    assert r2.status_code == 201
    beta_id = r2.json()["id"]

    list_resp2 = client.get("/admin/templates", headers=HEADERS)
    alpha_updated = next(t for t in list_resp2.json() if t["id"] == alpha_id)
    beta_updated = next(t for t in list_resp2.json() if t["id"] == beta_id)
    assert alpha_updated["is_default"] is False
    assert beta_updated["is_default"] is True


def test_cannot_delete_default_template(client):
    list_resp = client.get("/admin/templates", headers=HEADERS)
    assert list_resp.status_code == 200
    default_tmpl = next((t for t in list_resp.json() if t["is_default"]), None)
    assert default_tmpl is not None

    del_resp = client.delete(f"/admin/templates/{default_tmpl['id']}", headers=HEADERS)
    assert del_resp.status_code == 400
    assert "Cannot delete the default template" in del_resp.json()["detail"]


def test_delete_custom_template(client):
    create_resp = client.post(
        "/admin/templates",
        headers=HEADERS,
        json={
            "name": "Temporary Template",
            "event_type": "work_anniversary",
            "subject_line": "Temp {{ name }}",
            "html_body": "<p>Temp</p>",
            "is_default": False,
        },
    )
    assert create_resp.status_code == 201
    tmpl_id = create_resp.json()["id"]

    del_resp = client.delete(f"/admin/templates/{tmpl_id}", headers=HEADERS)
    assert del_resp.status_code == 200

    list_resp = client.get("/admin/templates", headers=HEADERS)
    assert not any(t["id"] == tmpl_id for t in list_resp.json())


def test_employee_specific_template_rendered(db, default_org):
    vip_tmpl = EventTemplate(
        organization_id=default_org.id,
        name="VIP Executive Birthday",
        event_type=EventType.BIRTHDAY,
        variant_key="vip_birthday",
        subject_line="🌟 Executive Wishes, {{ name }}!",
        html_body="<div class='vip'>Happy Birthday to our leader {{ name }}!</div>",
        is_default=False,
        is_active=True,
    )
    db.add(vip_tmpl)
    db.commit()

    emp = make_employee(db, dob=date(1990, 5, 10))
    emp.birthday_template_id = vip_tmpl.id
    db.commit()

    event = EventLog(
        organization_id=emp.organization_id,
        employee_id=emp.id,
        event_type=EventType.BIRTHDAY,
        event_date=date(2026, 5, 10),
        status=EventStatus.PENDING,
        batch_id="2026-05-10",
    )
    db.add(event)
    db.commit()

    render_event(db, event)
    assert event.status == EventStatus.RENDERED
    assert event.template_id == vip_tmpl.id
    assert "Executive Wishes" in event.rendered_subject
    assert "vip" in event.rendered_html


def test_employee_fallback_to_default_template(db, default_org):
    emp = make_employee(db, dob=date(1992, 6, 15))
    emp.birthday_template_id = None
    db.commit()

    event = EventLog(
        organization_id=emp.organization_id,
        employee_id=emp.id,
        event_type=EventType.BIRTHDAY,
        event_date=date(2026, 6, 15),
        status=EventStatus.PENDING,
        batch_id="2026-06-15",
    )
    db.add(event)
    db.commit()

    render_event(db, event)
    assert event.status == EventStatus.RENDERED
    assert event.template_id is not None
    used_tmpl = db.get(EventTemplate, event.template_id)
    assert used_tmpl is not None
    assert used_tmpl.event_type == EventType.BIRTHDAY


def test_preview_template_endpoint(client):
    resp = client.post(
        "/admin/templates/preview",
        headers=HEADERS,
        json={
            "event_type": "birthday",
            "subject_line": "Happy Birthday {{ name }} from {{ company_name }}!",
            "html_body": "<div>Congrats {{ name }}!</div>",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Happy Birthday Alex Morgan from" in data["rendered_subject"]
    assert "Congrats Alex Morgan!" in data["rendered_html"]


def test_multi_tenant_template_isolation(client, db):
    from app.models import Organization
    import uuid

    # Create Org B
    org_b = Organization(
        id=str(uuid.uuid4()),
        name="Beta Innovations",
        slug="beta-innovations",
        api_key="beta-api-key-999",
        is_active=True,
    )
    db.add(org_b)
    db.commit()

    headers_a = {"x-api-key": "test-key"}
    headers_b = {"x-api-key": "beta-api-key-999"}

    # 1. Org A creates a template
    res_a = client.post(
        "/admin/templates",
        headers=headers_a,
        json={
            "name": "Org A Exclusive Design",
            "event_type": "birthday",
            "subject_line": "Org A Wishes {{ name }}",
            "html_body": "<h1>Org A Only</h1>",
            "is_default": False,
        },
    )
    assert res_a.status_code == 201
    tmpl_a_id = res_a.json()["id"]

    # 2. Org B creates a template
    res_b = client.post(
        "/admin/templates",
        headers=headers_b,
        json={
            "name": "Org B Exclusive Design",
            "event_type": "birthday",
            "subject_line": "Org B Wishes {{ name }}",
            "html_body": "<h1>Org B Only</h1>",
            "is_default": False,
        },
    )
    assert res_b.status_code == 201
    tmpl_b_id = res_b.json()["id"]

    # 3. Org A listing does NOT contain Org B template
    list_a = client.get("/admin/templates", headers=headers_a).json()
    ids_a = [t["id"] for t in list_a]
    assert tmpl_a_id in ids_a
    assert tmpl_b_id not in ids_a

    # 4. Org B listing does NOT contain Org A template
    list_b = client.get("/admin/templates", headers=headers_b).json()
    ids_b = [t["id"] for t in list_b]
    assert tmpl_b_id in ids_b
    assert tmpl_a_id not in ids_b

    # 5. Cross-tenant delete protection (Org A cannot delete Org B's template)
    del_cross = client.delete(f"/admin/templates/{tmpl_b_id}", headers=headers_a)
    assert del_cross.status_code == 404

    # 6. Cross-tenant employee template assignment protection
    emp_cross = client.post(
        "/admin/employees",
        headers=headers_a,
        json={
            "employee_code": "ISOLATION-001",
            "full_name": "Test Isolation",
            "email": "iso@example.com",
            "date_of_birth": "1995-01-01",
            "date_of_joining": "2020-01-01",
            "birthday_template_id": tmpl_b_id,  # belongs to Org B!
        },
    )
    assert emp_cross.status_code == 400
    assert "Invalid birthday template selected" in emp_cross.json()["detail"]
