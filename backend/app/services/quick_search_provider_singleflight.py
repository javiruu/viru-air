from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import QuickSearchProviderLock
from app.services.quick_search_execution import build_cache_source_hash
from app.services.quick_search_redis_lock import (
    RedisLockClient,
    acquire_redis_provider_lock,
    release_redis_provider_lock,
)


@dataclass(frozen=True, slots=True)
class QuickSearchProviderLease:
    lock_key: str
    lock_token: str
    expires_at: dt.datetime


def build_quick_search_provider_lock_key(
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    currency: str = "EUR",
) -> str:
    return build_cache_source_hash(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
        currency=currency,
    )


def acquire_quick_search_provider_lock(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    currency: str = "EUR",
    lock_ttl_seconds: int = 30,
    now: dt.datetime | None = None,
    redis_client: RedisLockClient | None = None,
) -> QuickSearchProviderLease | None:
    reference_now = now or utc_now_naive()
    ttl = max(1, int(lock_ttl_seconds))
    expires_at = reference_now + dt.timedelta(seconds=ttl)
    lock_key = build_quick_search_provider_lock_key(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
        currency=currency,
    )
    lock_token = uuid.uuid4().hex
    redis_attempt = acquire_redis_provider_lock(
        lock_key=lock_key,
        ttl_seconds=ttl,
        redis_client=redis_client,
    )
    match redis_attempt.status:
        case "acquired":
            if redis_attempt.lock_token is None:
                return None
            return QuickSearchProviderLease(
                lock_key=lock_key,
                lock_token=redis_attempt.lock_token,
                expires_at=expires_at,
            )
        case "busy":
            return None
        case "unavailable":
            pass

    if _try_insert_lock(
        db,
        lock_key=lock_key,
        lock_token=lock_token,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=travel_date,
        provider=provider,
        currency=currency,
        acquired_at=reference_now,
        expires_at=expires_at,
    ):
        return QuickSearchProviderLease(lock_key=lock_key, lock_token=lock_token, expires_at=expires_at)

    taken_over = db.execute(
        update(QuickSearchProviderLock)
        .where(QuickSearchProviderLock.lock_key == lock_key)
        .where(QuickSearchProviderLock.expires_at <= reference_now)
        .values(
            lock_token=lock_token,
            acquired_at=reference_now,
            expires_at=expires_at,
            updated_at=reference_now,
        )
    )
    if taken_over.rowcount != 1:
        db.rollback()
        return None
    db.commit()
    return QuickSearchProviderLease(lock_key=lock_key, lock_token=lock_token, expires_at=expires_at)


def release_quick_search_provider_lock(
    db: Session,
    *,
    lock_token: str,
    redis_client: RedisLockClient | None = None,
) -> bool:
    redis_released = release_redis_provider_lock(lock_token=lock_token, redis_client=redis_client)
    if redis_released is not None:
        return redis_released
    released = db.execute(
        delete(QuickSearchProviderLock).where(QuickSearchProviderLock.lock_token == lock_token)
    )
    if released.rowcount != 1:
        db.rollback()
        return False
    db.commit()
    return True


def _try_insert_lock(
    db: Session,
    *,
    lock_key: str,
    lock_token: str,
    origin_iata: str,
    destination_iata: str,
    travel_date: dt.date | str,
    provider: str,
    currency: str,
    acquired_at: dt.datetime,
    expires_at: dt.datetime,
) -> bool:
    try:
        db.add(
            QuickSearchProviderLock(
                lock_key=lock_key,
                origin_iata=str(origin_iata).strip().upper(),
                destination_iata=str(destination_iata).strip().upper(),
                travel_date=_normalize_travel_date(travel_date),
                provider=str(provider).strip().lower(),
                currency=str(currency).strip().upper(),
                lock_token=lock_token,
                acquired_at=acquired_at,
                expires_at=expires_at,
                created_at=acquired_at,
                updated_at=acquired_at,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


def _normalize_travel_date(value: dt.date | str) -> dt.date:
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    return value
