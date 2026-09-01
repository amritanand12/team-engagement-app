"""
Interactive Demo & Sandbox Service.
Generates realistic sample employee rosters with varied milestone dates
and provides a 1-click sandbox reset for live prospect demonstrations.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import DigestLog, EmployeeProfile, EventLog, Organization
from app.seed import seed_default_templates
from app.services.pipeline import run_tenant_pipeline

logger = logging.getLogger("engagement.demo")


def get_demo_roster_data(today: date) -> list[dict[str, Any]]:
    """
    Generates a realistic set of employees with milestones guaranteed to trigger:
    - 2 celebrating today (1 birthday, 1 milestone anniversary)
    - 1 double celebration today (birthday + anniversary)
    - 3 celebrating tomorrow / this week
    - 1 celebrating a 5-year milestone
    - 1 celebrating a 10-year milestone
    """
    return [
        {
            "employee_code": "DEMO-001",
            "full_name": "Aarav Sharma",
            "preferred_name": "Aarav",
            "email": "aarav.sharma@example.com",
            "department": "Engineering",
            "date_of_birth": date(1992, today.month, today.day),
            "date_of_joining": date(today.year - 3, 3, 15),
            "photo_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-002",
            "full_name": "Priya Patel",
            "preferred_name": "Priya",
            "email": "priya.patel@example.com",
            "department": "Product Design",
            "date_of_birth": date(1995, 7, 20),
            "date_of_joining": date(today.year - 5, today.month, today.day),  # 5-year milestone today!
            "photo_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-003",
            "full_name": "Marcus Vance",
            "preferred_name": "Marcus",
            "email": "marcus.vance@example.com",
            "department": "Executive Leadership",
            "date_of_birth": date(1985, today.month, today.day),  # Double celebration today!
            "date_of_joining": date(today.year - 10, today.month, today.day),  # 10-year milestone today!
            "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-004",
            "full_name": "Ananya Roy",
            "preferred_name": "Ananya",
            "email": "ananya.roy@example.com",
            "department": "Marketing",
            "date_of_birth": date(1996, (today + timedelta(days=1)).month, (today + timedelta(days=1)).day),
            "date_of_joining": date(today.year - 2, 6, 1),
            "photo_url": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-005",
            "full_name": "Rohan Gupta",
            "preferred_name": "Rohan",
            "email": "rohan.gupta@example.com",
            "department": "Operations",
            "date_of_birth": date(1991, (today + timedelta(days=2)).month, (today + timedelta(days=2)).day),
            "date_of_joining": date(today.year - 4, (today + timedelta(days=2)).month, (today + timedelta(days=2)).day),
            "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-006",
            "full_name": "Elena Rostova",
            "preferred_name": "Elena",
            "email": "elena.rostova@example.com",
            "department": "Engineering",
            "date_of_birth": date(1994, (today + timedelta(days=4)).month, (today + timedelta(days=4)).day),
            "date_of_joining": date(today.year - 1, 9, 10),
            "photo_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-007",
            "full_name": "Devin Clark",
            "preferred_name": "Devin",
            "email": "devin.clark@example.com",
            "department": "Finance",
            "date_of_birth": date(1989, 11, 14),
            "date_of_joining": date(today.year - 7, 4, 18),
            "photo_url": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-008",
            "full_name": "Fatima Al-Sayed",
            "preferred_name": "Fatima",
            "email": "fatima.alsayed@example.com",
            "department": "Human Resources",
            "date_of_birth": date(1993, 2, 28),
            "date_of_joining": date(today.year - 3, 1, 12),
            "photo_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-009",
            "full_name": "Liam O'Connor",
            "preferred_name": "Liam",
            "email": "liam.oconnor@example.com",
            "department": "Engineering",
            "date_of_birth": date(1998, 10, 5),
            "date_of_joining": date(today.year - 1, 10, 1),
            "photo_url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150&auto=format&fit=crop&q=80",
        },
        {
            "employee_code": "DEMO-010",
            "full_name": "Mei-Ling Chen",
            "preferred_name": "Mei",
            "email": "mei.chen@example.com",
            "department": "Product",
            "date_of_birth": date(1990, 8, 19),
            "date_of_joining": date(today.year - 6, 8, 15),
            "photo_url": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80",
        },
    ]


def reset_demo_organization(db: Session, org_id: str) -> tuple[int, int]:
    """
    Purges previous logs/employees for the demo organization, resets default templates,
    seeds demo employees, and runs today's pipeline.
    Returns: (employee_count, detected_events_count)
    """
    today = date.today()

    # 1. Clean up existing logs and employees
    db.query(DigestLog).filter(DigestLog.organization_id == org_id).delete()
    db.query(EventLog).filter(EventLog.organization_id == org_id).delete()
    db.query(EmployeeProfile).filter(EmployeeProfile.organization_id == org_id).delete()
    db.flush()

    # 2. Ensure default templates exist
    seed_default_templates(db, org_id)

    # 3. Seed fresh demo roster
    roster = get_demo_roster_data(today)
    for emp_data in roster:
        emp = EmployeeProfile(
            organization_id=org_id,
            employee_code=emp_data["employee_code"],
            full_name=emp_data["full_name"],
            preferred_name=emp_data["preferred_name"],
            email=emp_data["email"],
            department=emp_data["department"],
            date_of_birth=emp_data["date_of_birth"],
            date_of_joining=emp_data["date_of_joining"],
            photo_url=emp_data["photo_url"],
            is_active=True,
            last_synced_at=datetime.utcnow(),
        )
        db.add(emp)
    db.commit()

    # 4. Trigger initial pipeline run for today
    pipeline_res = run_tenant_pipeline(db, org_id, scan_date=today)
    return len(roster), pipeline_res.detected
