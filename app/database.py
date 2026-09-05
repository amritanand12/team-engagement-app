from __future__ import annotations

from contextlib import contextmanager
import logging
import os
import sqlite3
from typing import Any, Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

IS_FALLBACK_SQLITE: bool = False


def _configure_sqlite_connection(dbapi_connection: Any, connection_record: Any) -> None:
    """Set SQLite pragmas for data integrity and concurrency."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
        except Exception as exc:
            logger.debug("Failed to set SQLite pragma: %s", exc)
        finally:
            cursor.close()


def _build_sqlite_engine(url: str) -> Engine:
    """Creates a configured SQLite engine."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        db_path = url.replace("sqlite:///", "")
        parent_dir = os.path.dirname(os.path.abspath(db_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

    is_in_memory = url in ("sqlite://", "sqlite:///:memory:", "sqlite:///")
    connect_args = {"check_same_thread": False}
    engine_kwargs: dict[str, Any] = {}

    if is_in_memory:
        engine_kwargs["poolclass"] = StaticPool
    else:
        connect_args["timeout"] = 30

    eng = create_engine(url, connect_args=connect_args, **engine_kwargs)
    event.listen(eng, "connect", _configure_sqlite_connection)
    return eng


def _probe_connection(url: str, timeout_seconds: int = 2) -> tuple[bool, str]:
    """Attempts a quick connection probe to determine if the target DB is reachable."""
    connect_args: dict[str, Any] = {}
    if "psycopg" in url:
        connect_args["connect_timeout"] = timeout_seconds

    probe_engine = create_engine(url, connect_args=connect_args, pool_pre_ping=False)
    try:
        with probe_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, ""
    except Exception as exc:
        msg = str(exc).strip().splitlines()[0]
        if "(Background on this error" in msg:
            msg = msg.split("(Background on this error")[0].strip()
        return False, msg
    finally:
        probe_engine.dispose()


def create_resilient_engine(
    database_url: str | None = None,
    auto_fallback: bool | None = None,
    fallback_url: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[Engine, bool]:
    """
    Creates an engine. If Postgres connection fails and auto_fallback is enabled,
    automatically falls back to SQLite.
    Returns (engine, is_fallback).
    """
    target_url = database_url or settings.DATABASE_URL
    should_fallback = auto_fallback if auto_fallback is not None else settings.AUTO_FALLBACK_SQLITE
    fallback_target = fallback_url or settings.SQLITE_FALLBACK_URL
    probe_timeout = timeout_seconds if timeout_seconds is not None else settings.DB_CONNECT_TIMEOUT_SECONDS

    # 1. Directly SQLite
    if target_url.startswith("sqlite"):
        return _build_sqlite_engine(target_url), False

    # 2. Non-SQLite (e.g. PostgreSQL)
    if should_fallback:
        is_healthy, reason = _probe_connection(target_url, timeout_seconds=probe_timeout)
        if not is_healthy:
            masked_target = target_url.split("@")[-1] if "@" in target_url else target_url
            logger.info(
                "Primary database (%s) unavailable (%s). Falling back to SQLite.",
                masked_target,
                reason,
            )
            logger.info("Using SQLite fallback at: %s", fallback_target)
            return _build_sqlite_engine(fallback_target), True

    # 3. Use target engine (Postgres)
    eng = create_engine(target_url, pool_pre_ping=True)
    return eng, False


# Initialize module-level engine and sessionmaker
engine, IS_FALLBACK_SQLITE = create_resilient_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def reset_engine(
    database_url: str | None = None,
    auto_fallback: bool | None = None,
    fallback_url: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[Engine, bool]:
    """Rebuilds the module-level engine and SessionLocal (useful for testing)."""
    global engine, SessionLocal, IS_FALLBACK_SQLITE
    engine, IS_FALLBACK_SQLITE = create_resilient_engine(
        database_url=database_url,
        auto_fallback=auto_fallback,
        fallback_url=fallback_url,
        timeout_seconds=timeout_seconds,
    )
    SessionLocal.configure(bind=engine)
    return engine, IS_FALLBACK_SQLITE


def get_active_db_info() -> dict[str, Any]:
    return {
        "dialect": engine.dialect.name,
        "url": str(engine.url),
        "is_fallback": IS_FALLBACK_SQLITE,
    }


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for use outside request handlers (cron jobs, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _run_auto_migrations(eng: Engine) -> None:
    """Safely adds newly introduced columns to existing tables in SQLite or PostgreSQL."""
    from sqlalchemy import inspect
    inspector = inspect(eng)
    tables = inspector.get_table_names()

    with eng.connect() as conn:
        if "event_template" in tables:
            cols = [c["name"] for c in inspector.get_columns("event_template")]
            if "name" not in cols:
                conn.execute(text("ALTER TABLE event_template ADD COLUMN name VARCHAR(255) DEFAULT ''"))
            if "is_default" not in cols:
                conn.execute(text("ALTER TABLE event_template ADD COLUMN is_default BOOLEAN DEFAULT FALSE"))
            conn.execute(text("UPDATE event_template SET name = variant_key WHERE name IS NULL OR name = ''"))
            conn.execute(text("UPDATE event_template SET is_default = TRUE WHERE variant_key IN ('default', 'anniversary_default') AND is_default IS NOT TRUE"))
            conn.commit()

        if "employee_profile" in tables:
            cols = [c["name"] for c in inspector.get_columns("employee_profile")]
            if "birthday_template_id" not in cols:
                conn.execute(text("ALTER TABLE employee_profile ADD COLUMN birthday_template_id VARCHAR(36)"))
            if "anniversary_template_id" not in cols:
                conn.execute(text("ALTER TABLE employee_profile ADD COLUMN anniversary_template_id VARCHAR(36)"))
            conn.commit()


def init_db() -> None:
    """Create tables and apply incremental schema updates."""
    from app import models  # noqa: F401  (ensures models are registered on Base)

    Base.metadata.create_all(bind=engine)
    _run_auto_migrations(engine)

