from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import EmployeeProfile, EventLog, EventTemplate, Organization
from app.seed import seed_default_organization, seed_default_templates
from app.services.csv_importer import import_employees_from_csv
from app.services.mailer import MockMailer
from app.services.pipeline import run_tenant_pipeline


from app.database import get_db


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_multi_tenant_isolation(db, client):
    # Create Organization A
    org_a = Organization(
        name="Alpha Corp",
        slug="alpha",
        api_key="alpha-api-key",
        business_timezone="America/New_York",
        is_active=True,
    )
    # Create Organization B
    org_b = Organization(
        name="Beta Inc",
        slug="beta",
        api_key="beta-api-key",
        business_timezone="Europe/London",
        is_active=True,
    )
    db.add_all([org_a, org_b])
    db.commit()
    seed_default_templates(db, org_a.id)
    seed_default_templates(db, org_b.id)

    # Add employee with same code 'E001' to both orgs
    emp_a = EmployeeProfile(
        organization_id=org_a.id,
        employee_code="E001",
        full_name="Alpha Alice",
        email="alice@alpha.com",
        date_of_birth=date(1990, 5, 10),
        is_active=True,
    )
    emp_b = EmployeeProfile(
        organization_id=org_b.id,
        employee_code="E001",
        full_name="Beta Bob",
        email="bob@beta.com",
        date_of_birth=date(1992, 5, 10),
        is_active=True,
    )
    db.add_all([emp_a, emp_b])
    db.commit()

    # Query with Org A's key
    resp_a = client.get("/admin/employees", headers={"x-api-key": "alpha-api-key"})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total"] == 1
    assert data_a["items"][0]["full_name"] == "Alpha Alice"

    # Query with Org B's key
    resp_b = client.get("/admin/employees", headers={"x-api-key": "beta-api-key"})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["total"] == 1
    assert data_b["items"][0]["full_name"] == "Beta Bob"


def test_tenant_pipeline_isolation(db):
    org_a = Organization(name="Org A", slug="org-a", api_key="key-a", is_active=True)
    org_b = Organization(name="Org B", slug="org-b", api_key="key-b", is_active=True)
    db.add_all([org_a, org_b])
    db.commit()
    seed_default_templates(db, org_a.id)
    seed_default_templates(db, org_b.id)

    # Org A employee has birthday on Aug 22
    emp_a = EmployeeProfile(
        organization_id=org_a.id,
        employee_code="A1",
        full_name="Alice",
        email="alice@a.com",
        date_of_birth=date(1990, 8, 22),
        is_active=True,
    )
    # Org B employee has birthday on Sept 15
    emp_b = EmployeeProfile(
        organization_id=org_b.id,
        employee_code="B1",
        full_name="Bob",
        email="bob@b.com",
        date_of_birth=date(1990, 9, 15),
        is_active=True,
    )
    db.add_all([emp_a, emp_b])
    db.commit()

    mailer = MockMailer()
    result_a = run_tenant_pipeline(db, org_a.id, scan_date=date(2026, 8, 22), mailer=mailer)
    assert result_a.detected == 1
    assert result_a.sent == 1

    # Ensure no events logged for Org B on Aug 22
    events_b = db.query(EventLog).filter(EventLog.organization_id == org_b.id).all()
    assert len(events_b) == 0


def test_csv_import_success_and_validation(db):
    org = Organization(name="Test Org", slug="test-org", api_key="csv-test-key", is_active=True)
    db.add(org)
    db.commit()

    csv_data = """Employee ID,Full Name,Email,Date of Birth,Date of Joining,Department
EMP01,Karan Johar,karan@example.com,1985-04-12,2018-06-01,Entertainment
EMP02,Sara Ali,sara@example.com,12/08/1995,01/02/2021,Marketing
EMP03,Invalid Person,not-an-email,1990-01-01,2020-01-01,Sales
"""
    imported, updated, failed, errors = import_employees_from_csv(db, org.id, csv_data)
    assert imported == 2
    assert updated == 0
    assert failed == 1
    assert len(errors) == 1
    assert errors[0]["row"] == 4
    assert "Invalid email format" in errors[0]["error"]

    # Verify employees in database
    emps = db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org.id).all()
    assert len(emps) == 2
    codes = {e.employee_code for e in emps}
    assert codes == {"EMP01", "EMP02"}
