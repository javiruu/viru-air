from __future__ import annotations

import datetime as dt
import os

from app.core.time import utc_now_naive

_DEFAULT_REDIS_MAX_PAYLOAD_BYTES = max(1, int(os.getenv("QUICK_SEARCH_REDIS_MAX_PAYLOAD_BYTES", "65536")))


def redis_ttl(
    expires_at: dt.datetime,
    *,
    now: dt.datetime | None,
    max_ttl_seconds: int,
) -> int:
    remaining = int((expires_at - (now or utc_now_naive())).total_seconds())
    return min(max(0, remaining), max(1, int(max_ttl_seconds)))


def redis_payload_fits(
    payload: str,
    *,
    max_payload_bytes: int = _DEFAULT_REDIS_MAX_PAYLOAD_BYTES,
) -> bool:
    return len(payload.encode("utf-8")) <= max(1, int(max_payload_bytes))
