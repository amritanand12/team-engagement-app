from __future__ import annotations

from datetime import date

from app.models import EventLog, EventStatus, EventType
from app.services import digest as digest_service
from app.services.renderer import render_event
from tests.conftest import make_employee


def _rendered_event(db, emp, event_type, years=None, batch_id="2026-08-22"):
    event = EventLog(
        organization_id=emp.organization_id,
        employee_id=emp.id, event_type=event_type, event_date=date(2026, 8, 22),
        years=years, status=EventStatus.PENDING, batch_id=batch_id,
    )
    db.add(event)
    db.commit()
    render_event(db, event)
    db.commit()
    return event


def test_digest_groups_birthday_and_anniversary_separately(db):
    e1 = make_employee(db, code="E1", name="Asha", dob=date(1995, 8, 22))
    e2 = make_employee(db, code="E2", name="Ravi", doj=date(2021, 8, 22))
    ev1 = _rendered_event(db, e1, EventType.BIRTHDAY)
    ev2 = _rendered_event(db, e2, EventType.WORK_ANNIVERSARY, years=5)

    grouped = digest_service.group_events_for_digest([ev1, ev2])
    assert len(grouped["birthdays"]) == 1
    assert len(grouped["anniversaries"]) == 1
    assert grouped["combined_people"] == []


def test_digest_merges_same_employee_dual_events_into_combined_section(db):
    """An employee with BOTH a birthday and anniversary today must appear once,
    in the combined section — never as two separate list entries."""
    emp = make_employee(db, code="E1", name="Asha", dob=date(1995, 6, 15), doj=date(2020, 6, 15))
    ev1 = _rendered_event(db, emp, EventType.BIRTHDAY)
    ev2 = _rendered_event(db, emp, EventType.WORK_ANNIVERSARY, years=6)

    grouped = digest_service.group_events_for_digest([ev1, ev2])
    assert len(grouped["combined_people"]) == 1
    assert grouped["birthdays"] == []
    assert grouped["anniversaries"] == []
    assert grouped["combined_people"][0]["years"] == 6


def test_render_digest_returns_none_for_empty_batch():
    assert digest_service.render_digest([], date(2026, 8, 22)) is None


def test_render_digest_html_contains_all_names(db):
    e1 = make_employee(db, code="E1", name="Asha", dob=date(1995, 8, 22))
    e2 = make_employee(db, code="E2", name="Ravi", doj=date(2021, 8, 22))
    ev1 = _rendered_event(db, e1, EventType.BIRTHDAY)
    ev2 = _rendered_event(db, e2, EventType.WORK_ANNIVERSARY, years=5)

    html = digest_service.render_digest([ev1, ev2], date(2026, 8, 22))
    assert "Asha" in html
    assert "Ravi" in html


def test_digest_truncates_large_batches(db, monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    original = settings.DIGEST_MAX_VISIBLE_PER_SECTION
    settings.DIGEST_MAX_VISIBLE_PER_SECTION = 3
    try:
        events = []
        for i in range(12):
            emp = make_employee(db, code=f"E{i}", name=f"Person{i}", email=f"p{i}@example.com", dob=date(1995, 8, 22))
            events.append(_rendered_event(db, emp, EventType.BIRTHDAY))

        html = digest_service.render_digest(events, date(2026, 8, 22))
        assert "and 9 more" in html
    finally:
        settings.DIGEST_MAX_VISIBLE_PER_SECTION = original


def test_get_renderable_events_only_includes_rendered_or_sent(db):
    emp = make_employee(db, dob=date(1995, 8, 22))
    pending_event = EventLog(
        organization_id=emp.organization_id,
        employee_id=emp.id, event_type=EventType.BIRTHDAY, event_date=date(2026, 8, 22),
        status=EventStatus.PENDING, batch_id="2026-08-22",
    )
    failed_event = EventLog(
        organization_id=emp.organization_id,
        employee_id=emp.id, event_type=EventType.WORK_ANNIVERSARY, event_date=date(2026, 8, 22),
        status=EventStatus.FAILED, batch_id="2026-08-22", years=2,
    )
    db.add_all([pending_event, failed_event])
    db.commit()

    result = digest_service.get_renderable_events_for_batch(db, "2026-08-22", organization_id=emp.organization_id)
    assert result == []
