from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.database import get_db
from app.main import app
from app.models import EmployeeProfile, EventLog, EventStatus, EventType, Organization
from app.routers import superadmin as superadmin_router
from app.seed import seed_default_organization, seed_superadmin


@pytest.fixture()
def client(db):
    seed_superadmin(db)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _superadmin_token(client, db):
    seed_default_organization(db)
    response = client.post("/auth/login", json={"email": "admin@platform.local", "password": "admin123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_superadmin_requires_explicit_tenant_for_operations(client, db):
    token = _superadmin_token(client, db)
    response = client.get("/admin/employees", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert "No tenant selected" in response.json()["detail"]


def test_superadmin_directory_counts_dedicated_db_and_only_sent_events(client, db, monkeypatch):
    token = _superadmin_token(client, db)
    org = Organization(
        name="Dedicated Tenant",
        slug="dedicated-tenant",
        api_key="dedicated-key",
        is_db_configured=True,
        db_host="dedicated",
        db_name="dedicated",
        is_smtp_configured=True,
        is_setup_complete=True,
    )
    db.add(org)
    db.commit()

    tenant_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(tenant_engine)
    tenant_session = sessionmaker(bind=tenant_engine)()
    synced_at = datetime(2026, 10, 20, 10, 30)
    employee = EmployeeProfile(
        organization_id=org.id,
        employee_code="D-1",
        full_name="Tenant Employee",
        email="employee@example.com",
        last_synced_at=synced_at,
    )
    tenant_session.add(employee)
    tenant_session.flush()
    tenant_session.add_all([
        EventLog(organization_id=org.id, employee_id=employee.id, event_type=EventType.BIRTHDAY, event_date=date(2026, 10, 20), status=EventStatus.SENT, batch_id="2026-10-20"),
        EventLog(organization_id=org.id, employee_id=employee.id, event_type=EventType.WORK_ANNIVERSARY, event_date=date(2026, 10, 21), status=EventStatus.FAILED, batch_id="2026-10-21"),
    ])
    tenant_session.commit()
    tenant_session.close()
    monkeypatch.setattr(superadmin_router, "get_tenant_engine", lambda _org: tenant_engine)

    response = client.get("/superadmin/organizations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    record = next(row for row in response.json() if row["id"] == org.id)
    assert record["database_status"] == "connected"
    assert record["employee_count"] == 1
    assert record["event_count"] == 1
    assert record["is_db_configured"] is True
    assert record["is_smtp_configured"] is True
    assert record["is_setup_complete"] is True
    assert record["last_sync_at"].startswith("2026-10-20T10:30:00")
    tenant_engine.dispose()


def test_superadmin_directory_marks_unreachable_tenant_counts_unavailable(client, db, monkeypatch):
    token = _superadmin_token(client, db)
    org = Organization(
        name="Unavailable Tenant",
        slug="unavailable-tenant",
        api_key="unavailable-key",
        is_db_configured=True,
        db_host="invalid-host",
        db_name="tenant_db",
    )
    db.add(org)
    db.commit()

    def unavailable(_org):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(superadmin_router, "get_tenant_engine", unavailable)
    response = client.get("/superadmin/organizations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    record = next(row for row in response.json() if row["id"] == org.id)
    assert record["database_status"] == "unavailable"
    assert record["employee_count"] is None
    assert record["event_count"] is None
    assert record["last_sync_at"] is None


def test_tenant_operations_return_503_when_configured_database_is_unavailable(client, db, monkeypatch):
    org = Organization(
        name="Unreachable Tenant",
        slug="unreachable-tenant",
        api_key="unreachable-key",
        is_db_configured=True,
        db_host="invalid-host",
        db_name="tenant_db",
    )
    db.add(org)
    db.commit()
    monkeypatch.setattr(
        "app.routers.admin.get_tenant_engine",
        lambda _org: (_ for _ in ()).throw(RuntimeError("tenant database unavailable")),
    )

    response = client.get("/admin/employees", headers={"x-api-key": org.api_key})
    assert response.status_code == 503
    assert "tenant database unavailable" in response.json()["detail"]


def test_configured_tenant_engine_does_not_fall_back_to_platform(monkeypatch):
    from app import database

    org = Organization(
        id="broken-tenant",
        name="Broken Tenant",
        slug="broken-tenant",
        api_key="broken-key",
        is_db_configured=True,
        db_host="invalid-host",
        db_name="tenant_db",
    )

    def fail_engine(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(database, "get_tenant_db_url", lambda _org: "postgresql+psycopg2://invalid")
    monkeypatch.setattr(database, "create_engine", fail_engine)
    database.invalidate_tenant_engine(org.id)
    with pytest.raises(RuntimeError, match="Tenant database.*unavailable"):
        database.get_tenant_engine(org)
