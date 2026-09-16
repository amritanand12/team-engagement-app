"""
Delivery adapter. Kept thin and swappable so the scan/render/digest logic
never needs to know which provider is behind it.
"""
from __future__ import annotations

import logging
import smtplib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import mimetypes
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger("engagement.mailer")
settings = get_settings()


class MailSendError(Exception):
    pass


class BaseMailer(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, html: str, attachment_path: str | None = None) -> None:
        """Raise MailSendError on failure. Must not swallow exceptions silently."""


class SMTPMailer(BaseMailer):
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        from_address: str | None = None,
        use_tls: bool = True,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USERNAME
        self.password = password or settings.SMTP_PASSWORD
        self.from_address = from_address or settings.SMTP_FROM_ADDRESS
        self.use_tls = use_tls

    def send(self, to: str, subject: str, html: str, attachment_path: str | None = None) -> None:
        if self.host in ("smtp.example.com", "example.com", ""):
            raise MailSendError(
                f"SMTP host is set to placeholder '{self.host}'. "
                f"Set MAIL_PROVIDER=mock in .env for local testing, or configure a valid SMTP server."
            )

        if attachment_path and os.path.isfile(attachment_path):
            # multipart/related structure for RFC 2387 inline embedded images (cid:...)
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = to

            alt_part = MIMEMultipart("alternative")
            msg.attach(alt_part)
            alt_part.attach(MIMEText(html, "html", "utf-8"))

            try:
                ctype, encoding = mimetypes.guess_type(attachment_path)
                if ctype is None or encoding is not None:
                    ctype = "image/jpeg"
                maintype, subtype = ctype.split("/", 1)
                with open(attachment_path, "rb") as fp:
                    img_data = fp.read()

                if maintype == "image":
                    part = MIMEImage(img_data, _subtype=subtype)
                else:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(img_data)
                    encoders.encode_base64(part)

                filename = os.path.basename(attachment_path)
                part.add_header("Content-ID", "<celebration_photo>")
                part.add_header("Content-Disposition", "inline", filename=filename)
                msg.attach(part)
            except Exception as exc:
                logger.warning("Failed to attach inline photo %s: %s", attachment_path, exc)
        else:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = to
            msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.sendmail(self.from_address, [to], msg.as_string())
        except (smtplib.SMTPException, OSError) as exc:
            raise MailSendError(str(exc)) from exc


@dataclass
class MockMailer(BaseMailer):
    """In-memory mailer for tests and local dev. Records every send attempt."""
    sent: list[dict] = field(default_factory=list)
    fail_for: set[str] = field(default_factory=set)  # addresses to simulate failure for
    fail_times: int = 0  # if >0, fail this many times total before succeeding (for retry tests)

    def send(self, to: str, subject: str, html: str, attachment_path: str | None = None) -> None:
        if to in self.fail_for or self.fail_times > 0:
            if self.fail_times > 0:
                self.fail_times -= 1
            raise MailSendError(f"Simulated failure sending to {to}")
        self.sent.append({"to": to, "subject": subject, "html": html, "attachment_path": attachment_path})


def get_mailer(org: object | None = None) -> BaseMailer:
    if settings.MAIL_PROVIDER == "mock" or settings.TESTING:
        return MockMailer()
    if org and getattr(org, "smtp_host", None):
        from app.services.crypto import decrypt_credential
        raw_pw = getattr(org, "smtp_password", None)
        decrypted_pw = decrypt_credential(raw_pw) if raw_pw else None
        return SMTPMailer(
            host=getattr(org, "smtp_host", None),
            port=getattr(org, "smtp_port", None),
            username=getattr(org, "smtp_username", None),
            password=decrypted_pw,
            from_address=getattr(org, "smtp_from_address", None),
            use_tls=getattr(org, "smtp_use_tls", True),
        )
    return SMTPMailer()


def send_with_retry(
    mailer: BaseMailer,
    to: str,
    subject: str,
    html: str,
    attachment_path: str | None = None,
) -> tuple[bool, str | None]:
    """
    Returns (success, error_detail). Retries with linear backoff up to
    MAIL_MAX_RETRIES times. Never raises — caller decides how to record the outcome.
    """
    last_error: str | None = None
    for attempt in range(1, settings.MAIL_MAX_RETRIES + 1):
        try:
            mailer.send(to, subject, html, attachment_path=attachment_path)
            return True, None
        except MailSendError as exc:
            last_error = str(exc)
            logger.warning("Send attempt %d/%d to %s failed: %s", attempt, settings.MAIL_MAX_RETRIES, to, exc)
            if attempt < settings.MAIL_MAX_RETRIES:
                time.sleep(settings.MAIL_RETRY_BACKOFF_SECONDS * attempt)
    return False, last_error
