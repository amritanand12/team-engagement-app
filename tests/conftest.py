from __future__ import annotations

import os

os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["MAIL_PROVIDER"] = "mock"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["ADMIN_API_KEY"] = "test-key"

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import EmployeeProfile, Organization
from app.seed import seed_default_organization
from app.services.mailer import MockMailer


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    seed_default_organization(session)
    yield session
    session.close()


@pytest.fixture()
def default_org(db):
    return db.query(Organization).first()


@pytest.fixture()
def mock_mailer():
    return MockMailer()


def make_employee(
    db,
    *,
    organization_id: str | None = None,
    code="E001",
    name="Asha Rao",
    email="asha@example.com",
    dob: date | None = None,
    doj: date | None = None,
    is_active=True,
    photo_url=None,
    department="Engineering",
) -> EmployeeProfile:
    if not organization_id:
        org = db.query(Organization).first()
        organization_id = org.id if org else "default"

    emp = EmployeeProfile(
        organization_id=organization_id,
        employee_code=code,
        full_name=name,
        preferred_name=None,
        email=email,
        photo_url=photo_url,
        date_of_birth=dob,
        date_of_joining=doj,
        department=department,
        is_active=is_active,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@pytest.fixture()
def employee_factory(db):
    def _factory(**kwargs):
        return make_employee(db, **kwargs)
    return _factory
