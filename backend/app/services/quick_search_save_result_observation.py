from __future__ import annotations

import json
import logging
from typing import Protocol

from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightWatch, PriceSnapshot
from app.services.fare_memory_config import FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED
from app.services.revalidation_jobs import enqueue_revalidation_job
from app.services.watchlist_backfill import add_backfill_snapshots_for_watch, find_backfill_observations_for_watch
from app.services.watchlist_revalidation import route_fingerprint

logger = logging.getLogger("app.quick_search.save_result")


class SavedQuickSearchResultPayload(Protocol):
    price_total: float | None
    currency: str
    freshness_status: str | None
    requires_revalidation: bool | None
    validation_status: str | None


def handle_saved_result_observation(
    db: Session,
    watch: FlightWatch,
    payload: SavedQuickSearchResultPayload,
) -> None:
    if _saved_result_requires_revalidation(payload):
        _add_saved_result_backfill_snapshots(db, watch)
        _enqueue_saved_result_revalidation(db, watch, payload)
        return
    _seed_watch_snapshot_from_saved_result(db, watch, payload)
    _add_saved_result_backfill_snapshots(db, watch)


def _seed_watch_snapshot_from_saved_result(
    db: Session,
    watch: FlightWatch,
    payload: SavedQuickSearchResultPayload,
) -> None:
    if payload.price_total is None:
        return
    db.add(
        PriceSnapshot(
            watch_id=watch.id,
            raw_price=payload.price_total,
            raw_currency=payload.currency,
            provider="quick-search",
            is_stale=False,
        )
    )


def _saved_result_requires_revalidation(payload: SavedQuickSearchResultPayload) -> bool:
    revalidation_statuses = {
        "warm",
        "stale",
        "expired",
        "negative_fresh",
        "negative_stale",
        "provider_error_fresh",
        "provider_error_stale",
    }
    return payload.freshness_status in revalidation_statuses or payload.requires_revalidation is True


def _add_saved_result_backfill_snapshots(db: Session, watch: FlightWatch) -> None:
    if not FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED:
        return
    observations = find_backfill_observations_for_watch(db, watch)
    add_backfill_snapshots_for_watch(db, watch, observations)


def _enqueue_saved_result_revalidation(
    db: Session,
    watch: FlightWatch,
    payload: SavedQuickSearchResultPayload,
) -> None:
    target_fingerprint = route_fingerprint(
        watch.origin_iata,
        watch.destination_iata,
        watch.travel_date_local,
    )
    job, created = enqueue_revalidation_job(
        db,
        job_type="manual",
        target_type="route",
        target_fingerprint=target_fingerprint,
        provider="multi",
        priority=20,
        payload={
            "watch_id": watch.id,
            "user_id": watch.user_id,
            "reason": "saved_result_requires_revalidation",
            "freshness_status": payload.freshness_status,
            "validation_status": payload.validation_status,
        },
    )
    logger.info(
        json.dumps(
            {
                "event": "quick_search_save_result_revalidation_enqueued",
                "created": created,
                "job_id": job.id,
                "provider": job.provider,
                "target_fingerprint": target_fingerprint,
                "watch_id": watch.id,
                "freshness_status": payload.freshness_status,
                "validation_status": payload.validation_status,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
