from app.database import get_tenant_engine, provision_tenant_database
from app.models import EmployeeProfile, Organization


def test_unconfigured_tenant_database_fails_closed():
    org = Organization(id="unconfigured-strict", is_db_configured=False)
    try:
        get_tenant_engine(org)
    except RuntimeError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("An unconfigured tenant must not receive a database engine")


def test_tenant_employee_data_is_stored_outside_platform_database(db, tmp_path):
    tenant_path = tmp_path / "strict-tenant.sqlite"
    org = Organization(
        name="Isolated Tenant",
        slug="isolated-tenant",
        api_key="isolated-key",
        is_db_configured=True,
        db_host=f"sqlite:///{tenant_path.as_posix()}",
    )
    db.add(org)
    db.commit()

    ok, message = provision_tenant_database(org)
    assert ok, message
    tenant_engine = get_tenant_engine(org)

    from sqlalchemy.orm import Session

    with Session(tenant_engine) as tenant_db:
        tenant_db.add(EmployeeProfile(
            organization_id=org.id,
            employee_code="ONLY-TENANT",
            full_name="Tenant Data",
            email="tenant@example.com",
        ))
        tenant_db.commit()

    assert db.query(EmployeeProfile).filter_by(employee_code="ONLY-TENANT").count() == 0

