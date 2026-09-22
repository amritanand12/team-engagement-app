"""
Central configuration, loaded from environment variables.
Keep every tunable knob here so behaviour changes never require touching business logic.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# config.py is inside app/
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)
class Settings:
    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:newpassword@localhost:5432/engagement"
    )
    AUTO_FALLBACK_SQLITE: bool = os.getenv("AUTO_FALLBACK_SQLITE", "true").lower() == "true"
    SQLITE_FALLBACK_URL: str = os.getenv("SQLITE_FALLBACK_URL", "sqlite:///./engagement.db")
    DB_CONNECT_TIMEOUT_SECONDS: int = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "2"))

    # --- Redis (used for send-queue + distributed lock on the daily scan) ---
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # --- Scheduling ---
    # Business timezone the daily scan is pinned to. Do NOT use server-local time:
    # if the box runs in UTC and the company is IST, a birthday can be detected a day early/late.
    BUSINESS_TIMEZONE: str = os.getenv("BUSINESS_TIMEZONE", "Asia/Kolkata")
    DAILY_SCAN_HOUR: int = int(os.getenv("DAILY_SCAN_HOUR", "6"))
    DAILY_SCAN_MINUTE: int = int(os.getenv("DAILY_SCAN_MINUTE", "0"))
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"

    # --- Leap-year birthday policy ---
    # What to do with a Feb-29 birthday in a non-leap year.
    # "feb28" -> celebrate Feb 28, "mar1" -> celebrate Mar 1, "leap_only" -> skip entirely
    LEAP_DAY_POLICY: Literal["feb28", "mar1", "leap_only"] = os.getenv(
        "LEAP_DAY_POLICY", "feb28"
    )  # type: ignore[assignment]

    # --- Digest behaviour ---
    DIGEST_MAX_VISIBLE_PER_SECTION: int = int(os.getenv("DIGEST_MAX_VISIBLE_PER_SECTION", "10"))
    DEFAULT_DIGEST_CHANNEL_ID: str = os.getenv("DEFAULT_DIGEST_CHANNEL_ID", "company-wide-general")

    # --- Assets ---
    DEFAULT_AVATAR_URL: str = os.getenv(
        "DEFAULT_AVATAR_URL", "https://assets.example.com/default-avatar.png"
    )
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "Your Company")
    COMPANY_LOGO_URL: str = os.getenv("COMPANY_LOGO_URL", "https://assets.example.com/logo.png")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", os.getenv("FRONTEND_URL", "http://localhost:5173"))

    # --- Email delivery ---
    MAIL_PROVIDER: Literal["smtp", "mock"] = os.getenv("MAIL_PROVIDER", "smtp")  # type: ignore[assignment]
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_ADDRESS: str = os.getenv("SMTP_FROM_ADDRESS", "celebrations@example.com")
    MAIL_MAX_RETRIES: int = int(os.getenv("MAIL_MAX_RETRIES", "3"))
    MAIL_RETRY_BACKOFF_SECONDS: float = float(os.getenv("MAIL_RETRY_BACKOFF_SECONDS", "2.0"))

    # --- Admin API & Security ---
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "change-me-in-production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "") or os.getenv("SECRET_KEY", "engagement-default-jwt-secret-key-32chars")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "") or JWT_SECRET_KEY

    # --- HRMS sync ---
    HRMS_API_BASE_URL: str = os.getenv("HRMS_API_BASE_URL", "https://hrms.example.com/api")
    HRMS_API_TOKEN: str = os.getenv("HRMS_API_TOKEN", "")

    TESTING: bool = os.getenv("TESTING", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
