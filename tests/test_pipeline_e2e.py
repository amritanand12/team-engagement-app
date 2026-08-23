from __future__ import annotations

from datetime import date

from app.models import DigestStatus, EventLog, EventStatus, EventType
from app.services.mailer import MockMailer
from app.services.pipeline import run_daily_pipeline
from tests.conftest import make_employee


def test_full_pipeline_single_birthday(db):
    make_employee(db, code="E1", name="Asha", email="asha@example.com", dob=date(1995, 8, 22))
    mailer = MockMailer()

    result = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)

    assert result.detected == 1
    assert result.sent == 1
    assert result.failed == 0
    assert len(mailer.sent) == 2  # 1 individual email + 1 digest
    assert result.digest_status == DigestStatus.SENT.value


def test_pipeline_zero_events_skips_digest_without_sending_empty_message(db):
    make_employee(db, code="E1", name="Asha", email="asha@example.com", dob=date(1990, 1, 1))
    mailer = MockMailer()

    result = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)  # not Jan 1

    assert result.detected == 0
    assert result.digest_status == DigestStatus.EMPTY_SKIPPED.value
    assert mailer.sent == []


def test_pipeline_rerun_same_day_does_not_double_send(db):
    make_employee(db, code="E1", name="Asha", email="asha@example.com", dob=date(1995, 8, 22))
    mailer = MockMailer()

    result1 = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)
    assert result1.sent == 1
    assert len(mailer.sent) == 2  # individual + digest

    # Re-run the same day again (simulates cron misfiring twice, or manual re-trigger)
    result2 = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)

    # No new events detected (idempotent scan), and no new sends fired
    assert result2.detected == 1  # same single event still exists in that batch
    assert len(mailer.sent) == 2  # unchanged — nothing new was sent
    assert result2.digest_status == DigestStatus.SENT.value  # digest already-sent short-circuit


def test_pipeline_handles_two_events_same_day_for_different_employees(db):
    make_employee(db, code="E1", name="Asha", email="asha@example.com", dob=date(1995, 8, 22))
    make_employee(db, code="E2", name="Ravi", email="ravi@example.com", doj=date(2016, 8, 22))
    mailer = MockMailer()

    result = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)

    assert result.detected == 2
    assert result.sent == 2
    individual_sends = [m for m in mailer.sent if m["to"] in ("asha@example.com", "ravi@example.com")]
    assert len(individual_sends) == 2
    # Only ONE digest email should have gone out (to the channel), not two.
    digest_sends = [m for m in mailer.sent if m["to"] not in ("asha@example.com", "ravi@example.com")]
    assert len(digest_sends) == 1


def test_pipeline_single_employee_both_events_same_day(db):
    """Birthday AND anniversary on the same day for one person: two individual
    emails, but the digest must combine them into one entry (see test_digest.py)."""
    make_employee(
        db, code="E1", name="Asha", email="asha@example.com",
        dob=date(1990, 6, 15), doj=date(2018, 6, 15),
    )
    mailer = MockMailer()

    result = run_daily_pipeline(db, scan_date=date(2026, 6, 15), mailer=mailer)

    assert result.detected == 2  # birthday + anniversary, both logged
    assert result.sent == 2      # both individual emails sent
    individual_sends = [m for m in mailer.sent if m["to"] == "asha@example.com"]
    assert len(individual_sends) == 2
    digest_sends = [m for m in mailer.sent if m["to"] != "asha@example.com"]
    assert len(digest_sends) == 1
    assert "Double Celebration" in digest_sends[0]["html"]
    assert "Birthday &amp; 8-year" in digest_sends[0]["html"]  # doj 2018 -> 8 years by 2026


def test_pipeline_large_batch_of_events(db):
    for i in range(15):
        make_employee(
            db, code=f"E{i}", name=f"Person{i}", email=f"p{i}@example.com",
            dob=date(1990, 3, 3),
        )
    mailer = MockMailer()

    result = run_daily_pipeline(db, scan_date=date(2026, 3, 3), mailer=mailer)

    assert result.detected == 15
    assert result.sent == 15
    individual_sends = [m for m in mailer.sent if "example.com" in m["to"] and m["to"].startswith("p")]
    assert len(individual_sends) == 15


def test_pipeline_employee_missing_email_marks_event_failed_not_crash(db):
    make_employee(db, code="E1", name="NoEmail", email="", dob=date(1995, 8, 22))
    mailer = MockMailer()

    result = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)

    assert result.detected == 1
    assert result.failed == 1
    assert result.sent == 0


def test_pipeline_partial_send_failure_then_resend_does_not_duplicate(db):
    make_employee(db, code="E1", name="Asha", email="asha@example.com", dob=date(1995, 8, 22))

    # First run: mailer always fails for this address
    failing_mailer = MockMailer(fail_for={"asha@example.com"})
    from app.config import get_settings
    settings = get_settings()
    original_backoff = settings.MAIL_RETRY_BACKOFF_SECONDS
    settings.MAIL_RETRY_BACKOFF_SECONDS = 0
    try:
        result1 = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=failing_mailer)
        assert result1.failed == 1
        assert result1.sent == 0

        # Re-run pipeline with a working mailer (simulating "provider recovered, retry")
        working_mailer = MockMailer()
        result2 = run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=working_mailer)

        # The event was FAILED, not SENT, so the pipeline is free to retry it
        assert result2.sent == 1
        assert len(working_mailer.sent) == 2  # individual + digest

        # And no duplicate EventLog rows were created
        rows = db.query(EventLog).filter(EventLog.batch_id == "2026-08-22").all()
        assert len(rows) == 1
    finally:
        settings.MAIL_RETRY_BACKOFF_SECONDS = original_backoff


def test_pipeline_digest_never_resent_once_marked_sent(db):
    """If the pipeline is re-run after the digest already succeeded, it must not
    fire a second digest message even if new logic runs again."""
    make_employee(db, code="E1", name="Asha", email="asha@example.com", dob=date(1995, 8, 22))
    mailer = MockMailer()

    run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)
    digest_sends_after_first = [m for m in mailer.sent if m["to"] == "company-wide-general"]
    assert len(digest_sends_after_first) == 1

    run_daily_pipeline(db, scan_date=date(2026, 8, 22), mailer=mailer)
    digest_sends_after_second = [m for m in mailer.sent if m["to"] == "company-wide-general"]
    assert len(digest_sends_after_second) == 1  # unchanged
