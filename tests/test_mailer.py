from __future__ import annotations

from app.config import get_settings
from app.services.mailer import MockMailer, send_with_retry


def test_send_with_retry_succeeds_first_try():
    mailer = MockMailer()
    success, error = send_with_retry(mailer, "a@example.com", "Subj", "<p>hi</p>")
    assert success is True
    assert error is None
    assert len(mailer.sent) == 1


def test_send_with_retry_recovers_after_transient_failures():
    mailer = MockMailer(fail_times=2)  # fails twice, succeeds on 3rd attempt
    settings = get_settings()
    original_backoff = settings.MAIL_RETRY_BACKOFF_SECONDS
    settings.MAIL_RETRY_BACKOFF_SECONDS = 0  # speed up test
    try:
        success, error = send_with_retry(mailer, "a@example.com", "Subj", "<p>hi</p>")
        assert success is True
        assert len(mailer.sent) == 1
    finally:
        settings.MAIL_RETRY_BACKOFF_SECONDS = original_backoff


def test_send_with_retry_gives_up_after_max_retries():
    mailer = MockMailer(fail_for={"bad@example.com"})
    settings = get_settings()
    original_backoff = settings.MAIL_RETRY_BACKOFF_SECONDS
    settings.MAIL_RETRY_BACKOFF_SECONDS = 0
    try:
        success, error = send_with_retry(mailer, "bad@example.com", "Subj", "<p>hi</p>")
        assert success is False
        assert error is not None
        assert mailer.sent == []
    finally:
        settings.MAIL_RETRY_BACKOFF_SECONDS = original_backoff
