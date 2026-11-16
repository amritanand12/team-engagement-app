from __future__ import annotations

from datetime import date
import os
import tempfile
import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.database import (
    Base,
    create_resilient_engine,
    get_active_db_info,
    reset_engine,
)
from app.models import EmployeeProfile, EventLog, EventType, Organization
from app.services.scanner import DueEvent, persist_due_events


def test_direct_sqlite_engine():
    """Direct SQLite URL should initialize without probing."""
    engine, is_fallback = create_resilient_engine(database_url="sqlite://", auto_fallback=True)
    assert engine.dialect.name == "sqlite"
    assert is_fallback is False


def test_sqlite_pragmas_enabled():
    """SQLite engine should have foreign_keys enabled via connection listener."""
    engine, _ = create_resilient_engine(database_url="sqlite://")
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1


def test_sqlite_foreign_key_cascade():
    """Verify that CASCADE deletes work with our models on SQLite when foreign_keys=ON."""
    engine, _ = create_resilient_engine(database_url="sqlite://")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(name="Acme Corp", slug="acme", api_key="acme-key")
    session.add(org)
    session.commit()

    emp = EmployeeProfile(
        organization_id=org.id,
        employee_code="E100",
        full_name="Alice Smith",
        email="alice@example.com",
    )
    session.add(emp)
    session.commit()

    emp_id = emp.id
    assert session.query(EmployeeProfile).filter_by(id=emp_id).count() == 1

    # Deleting the organization should cascade-delete the employee
    session.delete(org)
    session.commit()

    session.expire_all()
    assert session.query(EmployeeProfile).filter_by(id=emp_id).count() == 0
    session.close()


def test_postgres_unreachable_falls_back_to_sqlite():
    """When PostgreSQL is down and auto_fallback=True, should fall back to SQLite."""
    # Use an unreachable port/host with a very low timeout (1s)
    fake_pg_url = "postgresql+psycopg2://nonexistent_user:pass@127.0.0.1:59999/nonexistent_db"
    fallback_file = tempfile.mktemp(suffix=".db")
    fallback_url = f"sqlite:///{fallback_file}"

    try:
        engine, is_fallback = create_resilient_engine(
            database_url=fake_pg_url,
            auto_fallback=True,
            fallback_url=fallback_url,
            timeout_seconds=1,
        )

        assert engine.dialect.name == "sqlite"
        assert is_fallback is True

        # Test creating tables and interacting with the fallback DB
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        org = Organization(name="Fallback Corp", slug="fallback", api_key="fallback-key")
        session.add(org)
        session.commit()
        assert session.query(Organization).count() == 1
        session.close()
    finally:
        if os.path.exists(fallback_file):
            try:
                os.remove(fallback_file)
            except OSError:
                pass


def test_scanner_upsert_on_sqlite_fallback():
    """Scanner persist_due_events upsert should work seamlessly on SQLite fallback engine."""
    engine, _ = create_resilient_engine(database_url="sqlite://")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(name="Scanner Org", slug="scanner-org", api_key="scanner-key")
    session.add(org)
    session.commit()

    emp = EmployeeProfile(
        organization_id=org.id,
        employee_code="E200",
        full_name="Bob Jones",
        email="bob@example.com",
    )
    session.add(emp)
    session.commit()

    due = [
        DueEvent(
            employee_id=emp.id,
            organization_id=org.id,
            event_type=EventType.BIRTHDAY,
            event_date=date(2026, 9, 3),
            years=None,
        )
    ]

    # First insert: 1 row
    inserted1 = persist_due_events(session, due, batch_id="2026-09-03")
    session.commit()
    assert inserted1 == 1

    # Second insert of the exact same event: 0 rows (idempotent ON CONFLICT DO NOTHING)
    inserted2 = persist_due_events(session, due, batch_id="2026-09-03")
    session.commit()
    assert inserted2 == 0

    assert session.query(EventLog).count() == 1
    session.close()


def test_reset_engine_and_db_info():
    """Test reset_engine and get_active_db_info helper."""
    reset_engine(database_url="sqlite://", auto_fallback=False)
    info = get_active_db_info()
    assert info["dialect"] == "sqlite"
    assert info["is_fallback"] is False
