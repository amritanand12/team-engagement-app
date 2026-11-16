"""
Redis-backed caching and distributed locking helpers.

Two responsibilities:
  1. CACHE  — wrap expensive DB queries (e.g. dashboard stats) with a short TTL.
              Uses Redis db/0 (same as REDIS_URL).
  2. LOCKS  — coordinate exclusive access across multiple worker processes so
              two workers cannot run the same day's pipeline concurrently.
              Uses atomic SET NX (set-if-not-exists) + compare-and-delete release.

Usage example — caching:
    result = get_or_set("stats:org123:30", ttl=60, compute_fn=lambda: expensive_query())

Usage example — locking:
    token = str(uuid.uuid4())
    if acquire_lock("pipeline_lock:org123:2025-01-15", token, ttl=1800):
        try:
            do_work()
        finally:
            release_lock("pipeline_lock:org123:2025-01-15", token)
    else:
        # Another worker already holds the lock
        raise Exception("Pipeline already running for this org/date")
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

import redis as redis_lib

from app.config import get_settings

logger = logging.getLogger("engagement.cache")
settings = get_settings()

# Module-level Redis client — thread-safe, connection-pooled.
_redis_client: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    """Return the shared Redis client, creating it lazily on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def cache_get(key: str) -> Any | None:
    """Return the cached value for key, or None on cache miss or Redis error."""
    try:
        raw = get_redis().get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.warning("Redis cache_get failed for key=%s: %s", key, exc)
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    """Store value as JSON under key with the given TTL (seconds)."""
    try:
        get_redis().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("Redis cache_set failed for key=%s: %s", key, exc)


def cache_delete(key: str) -> None:
    """Invalidate a single cache key."""
    try:
        get_redis().delete(key)
    except Exception as exc:
        logger.warning("Redis cache_delete failed for key=%s: %s", key, exc)


def get_or_set(key: str, ttl: int, compute_fn: Callable[[], Any]) -> Any:
    """
    Return the cached value for key if present; otherwise call compute_fn(),
    cache the result, and return it.

    Falls back to compute_fn() transparently if Redis is unavailable.
    """
    cached = cache_get(key)
    if cached is not None:
        logger.debug("Cache HIT: %s", key)
        return cached

    logger.debug("Cache MISS: %s — computing", key)
    result = compute_fn()
    cache_set(key, result, ttl)
    return result


# ---------------------------------------------------------------------------
# Distributed lock helpers
# ---------------------------------------------------------------------------

def acquire_lock(name: str, token: str, ttl: int) -> bool:
    """
    Try to acquire a named distributed lock.

    Uses atomic SET NX EX so only one caller succeeds across all processes/workers.

    Args:
        name:  Lock key (e.g. "pipeline_lock:org123:2025-01-15").
        token: Unique value identifying the lock holder (e.g. Celery task ID).
               Used in release_lock() to prevent one process releasing another's lock.
        ttl:   Lock expiry in seconds. Set conservatively to the max expected
               job duration so the lock auto-expires if the holder crashes.

    Returns True if the lock was acquired, False if already held by another process.
    """
    try:
        result = get_redis().set(name, token, nx=True, ex=ttl)
        acquired = result is True
        logger.debug("Lock %s acquire=%s token=%s", name, acquired, token)
        return acquired
    except Exception as exc:
        logger.warning("Redis acquire_lock failed for name=%s: %s", name, exc)
        # Fail open: if Redis is down, allow the caller to proceed.
        # For strict mutual exclusion in production, raise here instead.
        return True


def release_lock(name: str, token: str) -> bool:
    """
    Release a distributed lock only if the caller still owns it.

    Uses a Lua script for atomic compare-and-delete:
      if GET name == token: DEL name
    This prevents a timed-out lock from being released by a late-arriving process.

    Returns True if the lock was released, False if it had already expired or
    was held by a different token.
    """
    lua_script = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
    """
    try:
        result = get_redis().eval(lua_script, 1, name, token)
        released = result == 1
        logger.debug("Lock %s release=%s token=%s", name, released, token)
        return released
    except Exception as exc:
        logger.warning("Redis release_lock failed for name=%s: %s", name, exc)
        return False
