from __future__ import annotations

from datetime import date

import pytest

from app.config import get_settings
from app.models import EventType
from app.services import scanner
from tests.conftest import make_employee


def test_birthday_detected_on_matching_month_day(db):
    emp = make_employee(db, dob=date(1995, 8, 22))
    due = scanner.find_due_events(db, date(2026, 8, 22))
    assert len(due) == 1
    assert due[0].event_type == EventType.BIRTHDAY
    assert due[0].employee_id == emp.id


def test_birthday_not_detected_on_other_days(db):
    make_employee(db, dob=date(1995, 8, 22))
    due = scanner.find_due_events(db, date(2026, 8, 23))
    assert due == []


def test_work_anniversary_detected_and_years_computed(db):
    emp = make_employee(db, doj=date(2021, 8, 22))
    due = scanner.find_due_events(db, date(2026, 8, 22))
    assert len(due) == 1
    assert due[0].event_type == EventType.WORK_ANNIVERSARY
    assert due[0].years == 5


def test_join_day_itself_excluded_zero_year_anniversary(db):
    """An employee joining today should NOT get a 'work anniversary' email today."""
    make_employee(db, doj=date(2026, 8, 22))
    due = scanner.find_due_events(db, date(2026, 8, 22))
    assert due == []


def test_inactive_employee_excluded(db):
    make_employee(db, dob=date(1995, 8, 22), is_active=False)
    due = scanner.find_due_events(db, date(2026, 8, 22))
    assert due == []


def test_employee_with_both_events_same_day_returns_two_due_events(db):
    emp = make_employee(db, dob=date(1995, 6, 15), doj=date(2020, 6, 15))
    due = scanner.find_due_events(db, date(2026, 6, 15))
    types = {d.event_type for d in due}
    assert types == {EventType.BIRTHDAY, EventType.WORK_ANNIVERSARY}
    assert all(d.employee_id == emp.id for d in due)


@pytest.mark.parametrize(
    "policy,scan_date,should_fire,expected_years_check",
    [
        ("feb28", date(2027, 2, 28), True, None),   # non-leap year, feb28 policy
        ("feb28", date(2027, 3, 1), False, None),
        ("mar1", date(2027, 3, 1), True, None),
        ("mar1", date(2027, 2, 28), False, None),
        ("leap_only", date(2027, 2, 28), False, None),
        ("leap_only", date(2027, 3, 1), False, None),
    ],
)
def test_leap_day_birthday_policy(db, policy, scan_date, should_fire, expected_years_check):
    original_policy = scanner.settings.LEAP_DAY_POLICY
    scanner.settings.LEAP_DAY_POLICY = policy  # settings is an lru_cache singleton; mutate for this test
    try:
        make_employee(db, dob=date(2000, 2, 29))
        due = scanner.find_due_events(db, scan_date)
        fired = any(d.event_type == EventType.BIRTHDAY for d in due)
        assert fired == should_fire
    finally:
        scanner.settings.LEAP_DAY_POLICY = original_policy


def test_leap_day_birthday_fires_normally_in_leap_year(db):
    make_employee(db, dob=date(2000, 2, 29))
    due = scanner.find_due_events(db, date(2028, 2, 29))
    assert len(due) == 1
    assert due[0].event_type == EventType.BIRTHDAY


def test_persist_due_events_is_idempotent(db):
    make_employee(db, dob=date(1995, 8, 22))
    scan_date = date(2026, 8, 22)

    due1 = scanner.find_due_events(db, scan_date)
    inserted1 = scanner.persist_due_events(db, due1, scan_date.isoformat())
    db.commit()
    assert inserted1 == 1

    # Re-run the exact same scan (simulates cron firing twice, or manual re-trigger)
    due2 = scanner.find_due_events(db, scan_date)
    inserted2 = scanner.persist_due_events(db, due2, scan_date.isoformat())
    db.commit()
    assert inserted2 == 0  # no new rows created

    from app.models import EventLog
    total_rows = db.query(EventLog).filter(EventLog.batch_id == scan_date.isoformat()).count()
    assert total_rows == 1


def test_no_employees_no_events(db):
    due = scanner.find_due_events(db, date(2026, 8, 22))
    assert due == []
