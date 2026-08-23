from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
# StaticPool keeps a single persistent connection for sqlite (especially in-memory
# URLs), which is what makes state survive across FastAPI's per-request sessions
# and across threadpool workers during tests. Postgres uses the normal pool.
_engine_kwargs = {"poolclass": StaticPool} if _is_sqlite else {"pool_pre_ping": True}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


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


def init_db() -> None:
    """Create tables. In production, prefer Alembic migrations over this."""
    from app import models  # noqa: F401  (ensures models are registered on Base)

    Base.metadata.create_all(bind=engine)
