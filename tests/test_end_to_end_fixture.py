from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.models import DigestStatus, EventLog, EventStatus, EventType
from app.services.hrms_sync import sync_employees
from app.services.mailer import MockMailer
from app.services.pipeline import run_daily_pipeline

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hrms_fixture.json"


def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text())


def test_end_to_end_from_hrms_fixture(db):
    """
    Full pipeline against a synthetic HRMS dataset that intentionally includes:
    Meera (plain birthday), Larry (leap-day birthday, no photo), Dana (birthday
    AND 10yr anniversary same day), Ian (inactive — must be excluded), Nadia
    (birthday, no photo). Scan date is Aug 22, 2026.
    """
    records = _load_fixture()
    created, updated = sync_employees(db, records)
    assert created == 5
    assert updated == 0

    mailer = MockMailer()
    result = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)

    # Meera (birthday), Dana (birthday + 10yr anniversary), Nadia (birthday) = 4 events.
    # Ian is inactive -> excluded. Larry's birthday is Feb 29 -> irrelevant to Aug 22.
    assert result.detected == 4
    assert result.sent == 4
    assert result.failed == 0

    sent_addresses = [m["to"] for m in mailer.sent]
    assert "meera@example.com" in sent_addresses
    assert "dana@example.com" in sent_addresses
    assert "nadia@example.com" in sent_addresses
    assert "ian@example.com" not in sent_addresses  # inactive employee never emailed

    # Dana gets exactly two individual emails (birthday + anniversary), not one merged mail.
    assert sent_addresses.count("dana@example.com") == 2

    # Exactly one digest email, combining Dana's dual event.
    digest_sends = [m for m in mailer.sent if m["to"] == "company-wide-general"]
    assert len(digest_sends) == 1
    assert "Dual Event Dana" in digest_sends[0]["html"]
    assert "Double Celebration" in digest_sends[0]["html"]

    # Dana's anniversary should have used the 10yr milestone template.
    dana_anniv_event = (
        db.query(EventLog)
        .join(EventLog.employee)
        .filter(EventLog.event_type == EventType.WORK_ANNIVERSARY)
        .filter(EventLog.rendered_html.contains("Dana"))
        .first()
    )
    assert dana_anniv_event is not None
    assert "A Decade of Excellence" in dana_anniv_event.rendered_html

    # Nadia has no photo -> should have fallen back to the default avatar, not a broken <img>.
    nadia_event = (
        db.query(EventLog)
        .filter(EventLog.rendered_html.contains("No Photo Nadia"))
        .first()
    )
    from app.config import get_settings
    assert get_settings().DEFAULT_AVATAR_URL in nadia_event.rendered_html


def test_hrms_sync_is_idempotent_on_rerun(db):
    records = _load_fixture()
    created1, updated1 = sync_employees(db, records)
    assert created1 == 5

    created2, updated2 = sync_employees(db, records)
    assert created2 == 0
    assert updated2 == 5

    from app.models import EmployeeProfile
    assert db.query(EmployeeProfile).count() == 5
