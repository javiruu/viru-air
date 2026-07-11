from __future__ import annotations

import datetime as dt
import json
import logging
import os
from typing import Protocol, TypedDict

from app.core.time import utc_now_naive
from app.infrastructure.db.models import QuickSearchCacheEntry, QuickSearchNegativeCacheEntry
from app.infrastructure.redis_client import get_redis
from app.services.quick_search_execution import build_unit_cache_key
from app.services.quick_search_redis_payload_limits import redis_payload_fits, redis_ttl

logger = logging.getLogger(__name__)

_DEFAULT_REDIS_TTL_SECONDS = max(1, int(os.getenv("QUICK_SEARCH_REDIS_TTL_SECONDS", "300")))

RedisValue = bytes | str | None
RedisSetResult = bool | int | str | bytes | None


class RedisHotLayerClient(Protocol):
    def get(self, name: str) -> RedisValue: ...

    def setex(self, name: str, time: int, value: str) -> RedisSetResult: ...


class PositiveCachePayload(TypedDict):
    origin_iata: str
    destination_iata: str
    travel_date: str
    provider: str
    source_hash: str
    status: str
    ttl_seconds: int
    expires_at_utc: str
    captured_at_utc: str
    last_accessed_at_utc: str
    payload_json: str
    warnings_json: str
    provider_latency_ms: int | None


class NegativeCachePayload(TypedDict):
    negative_fingerprint: str
    scope: str
    reason: str
    provider: str | None
    canonical_request_json: str
    observed_at: str
    expires_at: str
    freshness_status: str
    retry_after_at: str | None
    hit_count: int
    created_at: str
    updated_at: str


def read_positive_cache_entry_from_redis(
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    source_hash: str,
    now: dt.datetime | None = None,
    redis_client: RedisHotLayerClient | None = None,
) -> QuickSearchCacheEntry | None:
    client = _resolve_client(redis_client)
    if client is None:
        return None
    try:
        raw_value = client.get(_positive_key(source_hash))
    except _redis_error_types():
        logger.debug("quick_search_redis_positive_read_failed", exc_info=True)
        return None
    if raw_value is None:
        return None
    payload = _decode_positive_payload(raw_value)
    if payload is None:
        return None
    key = build_unit_cache_key(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
    )
    if (
        payload["origin_iata"] != key[0]
        or payload["destination_iata"] != key[1]
        or payload["travel_date"] != key[2]
        or payload["provider"] != key[3]
        or payload["source_hash"] != source_hash
    ):
        return None
    expires_at = dt.datetime.fromisoformat(payload["expires_at_utc"])
    if expires_at <= (now or utc_now_naive()):
        return None
    return QuickSearchCacheEntry(
        origin_iata=payload["origin_iata"],
        destination_iata=payload["destination_iata"],
        travel_date=dt.date.fromisoformat(payload["travel_date"]),
        provider=payload["provider"],
        source_hash=payload["source_hash"],
        status=payload["status"],
        ttl_seconds=payload["ttl_seconds"],
        expires_at_utc=expires_at,
        captured_at_utc=dt.datetime.fromisoformat(payload["captured_at_utc"]),
        last_accessed_at_utc=dt.datetime.fromisoformat(payload["last_accessed_at_utc"]),
        payload_json=payload["payload_json"],
        warnings_json=payload["warnings_json"],
        provider_latency_ms=payload["provider_latency_ms"],
    )


def write_positive_cache_entry_to_redis(
    entry: QuickSearchCacheEntry,
    *,
    now: dt.datetime | None = None,
    redis_client: RedisHotLayerClient | None = None,
    max_ttl_seconds: int = _DEFAULT_REDIS_TTL_SECONDS,
) -> None:
    client = _resolve_client(redis_client)
    if client is None:
        return
    ttl = redis_ttl(entry.expires_at_utc, now=now, max_ttl_seconds=max_ttl_seconds)
    if ttl <= 0:
        return
    payload: PositiveCachePayload = {
        "origin_iata": entry.origin_iata,
        "destination_iata": entry.destination_iata,
        "travel_date": entry.travel_date.isoformat(),
        "provider": entry.provider,
        "source_hash": entry.source_hash,
        "status": entry.status,
        "ttl_seconds": int(entry.ttl_seconds),
        "expires_at_utc": entry.expires_at_utc.isoformat(),
        "captured_at_utc": entry.captured_at_utc.isoformat(),
        "last_accessed_at_utc": entry.last_accessed_at_utc.isoformat(),
        "payload_json": entry.payload_json,
        "warnings_json": entry.warnings_json,
        "provider_latency_ms": entry.provider_latency_ms,
    }
    _safe_setex(client, _positive_key(entry.source_hash), ttl, json.dumps(payload, sort_keys=True))


def read_negative_cache_entry_from_redis(
    *,
    negative_fingerprint: str,
    now: dt.datetime | None = None,
    redis_client: RedisHotLayerClient | None = None,
) -> QuickSearchNegativeCacheEntry | None:
    client = _resolve_client(redis_client)
    if client is None:
        return None
    try:
        raw_value = client.get(_negative_key(negative_fingerprint))
    except _redis_error_types():
        logger.debug("quick_search_redis_negative_read_failed", exc_info=True)
        return None
    if raw_value is None:
        return None
    payload = _decode_negative_payload(raw_value)
    if payload is None or payload["negative_fingerprint"] != negative_fingerprint:
        return None
    expires_at = dt.datetime.fromisoformat(payload["expires_at"])
    if expires_at <= (now or utc_now_naive()):
        return None
    retry_after_at = (
        dt.datetime.fromisoformat(payload["retry_after_at"])
        if payload["retry_after_at"] is not None
        else None
    )
    return QuickSearchNegativeCacheEntry(
        negative_fingerprint=payload["negative_fingerprint"],
        scope=payload["scope"],
        reason=payload["reason"],
        provider=payload["provider"],
        canonical_request_json=payload["canonical_request_json"],
        observed_at=dt.datetime.fromisoformat(payload["observed_at"]),
        expires_at=expires_at,
        freshness_status=payload["freshness_status"],
        retry_after_at=retry_after_at,
        hit_count=int(payload["hit_count"]),
        created_at=dt.datetime.fromisoformat(payload["created_at"]),
        updated_at=dt.datetime.fromisoformat(payload["updated_at"]),
    )


def write_negative_cache_entry_to_redis(
    entry: QuickSearchNegativeCacheEntry,
    *,
    now: dt.datetime | None = None,
    redis_client: RedisHotLayerClient | None = None,
    max_ttl_seconds: int = _DEFAULT_REDIS_TTL_SECONDS,
) -> None:
    client = _resolve_client(redis_client)
    if client is None:
        return
    ttl = redis_ttl(entry.expires_at, now=now, max_ttl_seconds=max_ttl_seconds)
    if ttl <= 0:
        return
    payload: NegativeCachePayload = {
        "negative_fingerprint": entry.negative_fingerprint,
        "scope": entry.scope,
        "reason": entry.reason,
        "provider": entry.provider,
        "canonical_request_json": entry.canonical_request_json,
        "observed_at": entry.observed_at.isoformat(),
        "expires_at": entry.expires_at.isoformat(),
        "freshness_status": entry.freshness_status,
        "retry_after_at": entry.retry_after_at.isoformat() if entry.retry_after_at else None,
        "hit_count": int(entry.hit_count or 0),
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }
    _safe_setex(
        client,
        _negative_key(entry.negative_fingerprint),
        ttl,
        json.dumps(payload, sort_keys=True),
    )


def _resolve_client(redis_client: RedisHotLayerClient | None) -> RedisHotLayerClient | None:
    return redis_client if redis_client is not None else get_redis()


def _positive_key(source_hash: str) -> str:
    return f"qs:result:{source_hash}"


def _negative_key(negative_fingerprint: str) -> str:
    return f"qs:negative:{negative_fingerprint}"


def _safe_setex(client: RedisHotLayerClient, name: str, ttl: int, payload: str) -> None:
    if not redis_payload_fits(payload):
        logger.debug("quick_search_redis_payload_too_large key=%s bytes=%s", name, len(payload.encode("utf-8")))
        return
    try:
        client.setex(name, ttl, payload)
    except _redis_error_types():
        logger.debug("quick_search_redis_write_failed key=%s", name, exc_info=True)


def _decode_positive_payload(raw_value: bytes | str) -> PositiveCachePayload | None:
    try:
        decoded = json.loads(raw_value.decode() if isinstance(raw_value, bytes) else raw_value)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    required = set(PositiveCachePayload.__annotations__)
    if not required.issubset(decoded):
        return None
    return decoded


def _decode_negative_payload(raw_value: bytes | str) -> NegativeCachePayload | None:
    try:
        decoded = json.loads(raw_value.decode() if isinstance(raw_value, bytes) else raw_value)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    required = set(NegativeCachePayload.__annotations__)
    if not required.issubset(decoded):
        return None
    return decoded


def _redis_error_types() -> tuple[type[BaseException], ...]:
    try:
        from redis.exceptions import RedisError
    except ImportError:
        return (ConnectionError, TimeoutError, OSError)
    return (RedisError, ConnectionError, TimeoutError, OSError)
