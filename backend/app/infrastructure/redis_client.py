"""Lazy Redis client for the quick-search shared cache hot layer.

Provides a singleton Redis connection that is only established
when REDIS_URL is configured. If Redis is unavailable or not
configured, get_redis() returns None gracefully.

Usage:
    from app.infrastructure.redis_client import get_redis

    r = get_redis()
    if r is not None:
        r.setex("qs:AGP:TSF:2026-12-25", 300, payload)
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis as _redis_mod
    Redis = _redis_mod.Redis

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None
_redis_checked: bool = False


def get_redis() -> Redis | None:
    """Return a Redis client if configured and reachable, or None.

    The connection is established once (lazy singleton). If the first
    connection attempt fails, subsequent calls return None immediately
    (no retry storm).

    Set REDIS_URL to enable Redis. Example: redis://localhost:6379/0
    """
    global _redis_client, _redis_checked

    if _redis_checked:
        return _redis_client

    _redis_checked = True

    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        logger.debug("redis_skipped_no_url")
        return None

    # Note: two threads may race past _redis_checked simultaneously.
    # This is benign — both would attempt connection, the second
    # overwrites the first. Redis connections are cheap and idempotent.
    try:
        import redis as _redis

        _redis_client = _redis.from_url(
            url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=False,
        )
        _redis_client.ping()
        logger.info("redis_connected url=%s", url)
        return _redis_client
    except Exception:
        logger.warning("redis_unavailable url=%s", url, exc_info=True)
        if _redis_client is not None:
            try:
                _redis_client.close()
            except Exception:
                pass
        _redis_client = None
        return None
