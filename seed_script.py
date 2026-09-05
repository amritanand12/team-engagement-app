from datetime import date
from app.database import session_scope
from app.models import EmployeeProfile, Organization

TODAY = date(2026, 8, 23)  # match whatever scan_date you'll trigger

with session_scope() as db:
    org = db.query(Organization).first()
    if not org:
        raise RuntimeError("No organization found. Please run init_db and seed_default_organization first.")

    # Employee 1: birthday today only
    db.add(EmployeeProfile(
        organization_id=org.id,
        employee_code="TEST-001",
        full_name="Asha Rao",
        email="anandamrit309@gmail.com",   # <-- put YOUR real inbox here
        date_of_birth=date(1995, TODAY.month, TODAY.day),
        department="Engineering",
        is_active=True,
    ))

    # Employee 2: work anniversary today only (5 years -> uses the 5yr template)
    db.add(EmployeeProfile(
        organization_id=org.id,
        employee_code="TEST-002",
        full_name="Ravi Kumar",
        email="amritanand850@gmail.com",   # <-- same or a second inbox you can check
        date_of_joining=date(TODAY.year - 5, TODAY.month, TODAY.day),
        department="Sales",
        is_active=True,
    ))

    # Employee 3: BOTH birthday and anniversary today (10 years -> uses the 10yr template)
    db.add(EmployeeProfile(
        organization_id=org.id,
        employee_code="TEST-003",
        full_name="Priya Nair",
        email="anandamrit1929@gmail.com",
        date_of_birth=date(1990, TODAY.month, TODAY.day),
        date_of_joining=date(TODAY.year - 10, TODAY.month, TODAY.day),
        department="Design",
        is_active=True,
    ))

print("added 3 employees")