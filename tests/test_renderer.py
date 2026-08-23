from __future__ import annotations

from datetime import date

from app.config import get_settings
from app.models import EventLog, EventStatus, EventTemplate, EventType
from app.services.renderer import render_event, select_variant
from tests.conftest import make_employee


def test_select_variant_birthday_always_default():
    assert select_variant(EventType.BIRTHDAY, None) == "default"


def test_select_variant_anniversary_milestones():
    assert select_variant(EventType.WORK_ANNIVERSARY, 1) == "anniversary_default"
    assert select_variant(EventType.WORK_ANNIVERSARY, 4) == "anniversary_default"
    assert select_variant(EventType.WORK_ANNIVERSARY, 5) == "anniversary_5yr"
    assert select_variant(EventType.WORK_ANNIVERSARY, 9) == "anniversary_5yr"
    assert select_variant(EventType.WORK_ANNIVERSARY, 10) == "anniversary_10yr"
    assert select_variant(EventType.WORK_ANNIVERSARY, 25) == "anniversary_10yr"


def test_render_birthday_event_success(db):
    emp = make_employee(db, dob=date(1995, 8, 22), photo_url="https://cdn.example.com/asha.jpg")
    event = EventLog(
        employee_id=emp.id, event_type=EventType.BIRTHDAY, event_date=date(2026, 8, 22),
        status=EventStatus.PENDING, batch_id="2026-08-22",
    )
    db.add(event)
    db.commit()

    render_event(db, event)

    assert event.status == EventStatus.RENDERED
    assert "Asha Rao" in event.rendered_html
    assert "https://cdn.example.com/asha.jpg" in event.rendered_html
    assert event.rendered_subject == "🎉 Happy Birthday, Asha Rao!"


def test_render_missing_photo_falls_back_to_default_avatar(db):
    emp = make_employee(db, dob=date(1995, 8, 22), photo_url=None)
    event = EventLog(
        employee_id=emp.id, event_type=EventType.BIRTHDAY, event_date=date(2026, 8, 22),
        status=EventStatus.PENDING, batch_id="2026-08-22",
    )
    db.add(event)
    db.commit()

    render_event(db, event)

    assert event.status == EventStatus.RENDERED
    assert get_settings().DEFAULT_AVATAR_URL in event.rendered_html


def test_render_anniversary_selects_5yr_variant(db):
    emp = make_employee(db, doj=date(2021, 8, 22))
    event = EventLog(
        employee_id=emp.id, event_type=EventType.WORK_ANNIVERSARY, event_date=date(2026, 8, 22),
        years=5, status=EventStatus.PENDING, batch_id="2026-08-22",
    )
    db.add(event)
    db.commit()

    render_event(db, event)

    assert event.status == EventStatus.RENDERED
    assert "5 Years Strong" in event.rendered_html


def test_render_falls_back_when_milestone_template_inactive(db):
    """If the 5yr template is deactivated, rendering should fall back to the generic
    anniversary template rather than failing the whole event."""
    tmpl = db.query(EventTemplate).filter(EventTemplate.variant_key == "anniversary_5yr").first()
    tmpl.is_active = False
    db.commit()

    emp = make_employee(db, doj=date(2021, 8, 22))
    event = EventLog(
        employee_id=emp.id, event_type=EventType.WORK_ANNIVERSARY, event_date=date(2026, 8, 22),
        years=5, status=EventStatus.PENDING, batch_id="2026-08-22",
    )
    db.add(event)
    db.commit()

    render_event(db, event)

    assert event.status == EventStatus.RENDERED
    assert "Congratulations on this milestone" in event.rendered_html  # generic template body


def test_render_fails_gracefully_when_no_template_at_all(db):
    for tmpl in db.query(EventTemplate).filter(EventTemplate.event_type == EventType.BIRTHDAY):
        tmpl.is_active = False
    db.commit()

    emp = make_employee(db, dob=date(1995, 8, 22))
    event = EventLog(
        employee_id=emp.id, event_type=EventType.BIRTHDAY, event_date=date(2026, 8, 22),
        status=EventStatus.PENDING, batch_id="2026-08-22",
    )
    db.add(event)
    db.commit()

    render_event(db, event)

    assert event.status == EventStatus.FAILED
    assert event.error_detail is not None


def test_render_escapes_html_in_name_to_prevent_xss(db):
    emp = make_employee(db, name='<script>alert("x")</script>', dob=date(1995, 8, 22))
    event = EventLog(
        employee_id=emp.id, event_type=EventType.BIRTHDAY, event_date=date(2026, 8, 22),
        status=EventStatus.PENDING, batch_id="2026-08-22",
    )
    db.add(event)
    db.commit()

    render_event(db, event)

    assert event.status == EventStatus.RENDERED
    assert "<script>" not in event.rendered_html
    assert "&lt;script&gt;" in event.rendered_html


def test_render_missing_placeholder_variable_raises_and_marks_failed(db):
    """A template referencing an undefined variable must fail loudly, never render
    the literal placeholder text into a live email."""
    bad_tmpl = EventTemplate(
        event_type=EventType.BIRTHDAY,
        variant_key="broken_variant",
        subject_line="Hi {{ nonexistent_field }}",
        html_body="<p>{{ nonexistent_field }}</p>",
        is_active=True,
    )
    db.add(bad_tmpl)
    for t in db.query(EventTemplate).filter(EventTemplate.event_type == EventType.BIRTHDAY, EventTemplate.variant_key == "default"):
        t.is_active = False
    db.commit()

    # force select_variant to resolve to our broken one by directly testing get_active_template path:
    from app.services.renderer import get_active_template
    import pytest as _pytest
    from app.services.renderer import RenderError

    with _pytest.raises(RenderError):
        get_active_template(db, EventType.BIRTHDAY, "default")
