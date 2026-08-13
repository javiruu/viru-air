from __future__ import annotations

import logging
import os
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis as _redis_mod
    Redis = _redis_mod.Redis

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None
_redis_checked_at: float | None = None
_redis_lock = threading.Lock()
_redis_retry_seconds = max(1.0, float(os.getenv("REDIS_RETRY_SECONDS", "15")))


def get_redis() -> Redis | None:
    global _redis_client, _redis_checked_at

    now = time.monotonic()
    if _redis_checked_at is not None and now - _redis_checked_at < _redis_retry_seconds:
        return _redis_client

    with _redis_lock:
        now = time.monotonic()
        if _redis_checked_at is not None and now - _redis_checked_at < _redis_retry_seconds:
            return _redis_client
        _redis_checked_at = now
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            logger.debug("redis_skipped_no_url")
            return None
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
