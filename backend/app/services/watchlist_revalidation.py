from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult
from app.domain.vocabulary import WATCH_STATUS_TRACKABLE
from app.infrastructure.db.models import FlightWatch, RevalidationJob
from app.infrastructure.providers.flight_provider import MultiSourceFlightProvider
from app.services.quick_search_cache_service import (
    deserialize_fetch_result,
    get_fresh_entry,
    serialize_fetch_result,
    set_cache_entry,
)
from app.services.quick_search_execution import build_cache_source_hash, classify_cache_result
from app.services.revalidation_jobs import (
    claim_next_revalidation_job,
    complete_revalidation_job,
    enqueue_revalidation_job,
    fail_revalidation_job,
    find_active_revalidation_job,
)
from app.services.watchlist_refresh_policy import evaluate_route_freshness, latest_snapshot_by_watch_ids
from app.services.watchlist_snapshots import (
    persist_changed_snapshots_for_watches,
    select_canonical_refresh_flight,
)

logger = logging.getLogger("app.watchlist")

WATCH_SHARED_CACHE_ENABLED = os.getenv("QUICK_SEARCH_SHARED_CACHE_ENABLED", "false").strip().lower() == "true"
WATCHLIST_STARTUP_REFRESH_ENABLED = (
    os.getenv("WATCHLIST_STARTUP_REFRESH_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
)
WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS = max(
    0, int(os.getenv("WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS", "14400"))
)

STARTUP_REFRESH_JOB_TYPE = "startup_refresh"
ROUTE_REVALIDATION_JOB_TYPES = (
    "manual",
    "boot_warmup",
    STARTUP_REFRESH_JOB_TYPE,
)

provider = MultiSourceFlightProvider()


@dataclass(frozen=True, slots=True)
class RouteRevalidationResult:
    status: str
    watch_count: int
    source: str
    provider_error: str | None = None


def route_fingerprint(origin_iata: str, destination_iata: str, travel_date_local: Date) -> str:
    return f"route:{origin_iata}:{destination_iata}:{travel_date_local.isoformat()}"


def parse_route_fingerprint(target_fingerprint: str) -> tuple[str, str, Date]:
    prefix, origin_iata, destination_iata, travel_date_text = target_fingerprint.split(":", 3)
    if prefix != "route":
        raise ValueError(f"Unsupported target fingerprint: {target_fingerprint}")
    return origin_iata, destination_iata, Date.fromisoformat(travel_date_text)


def enqueue_startup_refresh_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    provider_name: str = "multi",
) -> dict[str, object]:
    reference_now = now or utc_now_naive()
    active_watches = db.scalars(
        select(FlightWatch)
        .where(FlightWatch.status.in_(WATCH_STATUS_TRACKABLE))
        .where(FlightWatch.travel_date_local >= reference_now.date())
        .order_by(FlightWatch.travel_date_local.asc(), FlightWatch.created_at.asc(), FlightWatch.id.asc())
    ).all()
    routes: dict[tuple[str, str, Date], list[FlightWatch]] = {}
    for watch in active_watches:
        routes.setdefault((watch.origin_iata, watch.destination_iata, watch.travel_date_local), []).append(watch)

    latest_snapshot_by_watch = latest_snapshot_by_watch_ids(db, [watch.id for watch in active_watches])
    enqueued_count = 0
    skipped_due_lock_count = 0
    stale_route_count = 0
    jobs: list[dict[str, object]] = []

    for route_key, watches in routes.items():
        freshness = evaluate_route_freshness(
            watches=watches,
            latest_snapshot_by_watch=latest_snapshot_by_watch,
            now=reference_now,
            max_age_seconds=WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS,
        )
        if freshness.needs_refresh:
            stale_route_count += 1
        origin_iata, destination_iata, travel_date_local = route_key
        target_fingerprint = route_fingerprint(origin_iata, destination_iata, travel_date_local)
        if not freshness.needs_refresh:
            jobs.append(
                {
                    "target_fingerprint": target_fingerprint,
                    "job_id": None,
                    "status": "fresh_skipped",
                    "reason": freshness.state,
                    "watch_count": len(watches),
                }
            )
            continue

        active_job = find_active_revalidation_job(
            db,
            target_type="route",
            target_fingerprint=target_fingerprint,
            provider=provider_name,
        )
        if active_job is not None:
            skipped_due_lock_count += 1
            jobs.append(
                {
                    "target_fingerprint": target_fingerprint,
                    "job_id": active_job.id,
                    "status": "duplicate_locked",
                    "reason": freshness.state,
                    "watch_count": len(watches),
                }
            )
            continue

        job, created = enqueue_revalidation_job(
            db,
            job_type=STARTUP_REFRESH_JOB_TYPE,
            target_type="route",
            target_fingerprint=target_fingerprint,
            provider=provider_name,
            priority=15 if freshness.needs_refresh else 25,
            scheduled_at=reference_now,
            payload={
                "origin_iata": origin_iata,
                "destination_iata": destination_iata,
                "travel_date_local": travel_date_local.isoformat(),
                "reason": freshness.state,
                "oldest_snapshot_age_seconds": freshness.oldest_snapshot_age_seconds,
                "watch_count": len(watches),
            },
        )
        if created:
            enqueued_count += 1
        else:
            skipped_due_lock_count += 1
        jobs.append(
            {
                "target_fingerprint": target_fingerprint,
                "job_id": job.id,
                "status": job.status if created else "duplicate_locked",
                "reason": freshness.state,
                "watch_count": len(watches),
            }
        )

    return {
        "event": "watchlist_startup_refresh_scheduled",
        "enabled": WATCHLIST_STARTUP_REFRESH_ENABLED,
        "evaluated_route_count": len(routes),
        "stale_route_count": stale_route_count,
        "enqueued_job_count": enqueued_count,
        "skipped_due_lock_count": skipped_due_lock_count,
        "max_age_seconds": WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS,
        "generated_at": reference_now.isoformat(),
        "jobs": jobs,
    }


def log_enqueued_startup_refresh_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    provider_name: str = "multi",
) -> dict[str, object]:
    report = enqueue_startup_refresh_jobs(db, now=now, provider_name=provider_name)
    logger.info(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


def process_due_route_revalidation_jobs(
    session_factory,
    *,
    max_jobs: int | None = None,
    provider_client: MultiSourceFlightProvider | None = None,
) -> dict[str, object]:
    processed_count = 0
    refreshed_count = 0
    skipped_count = 0
    failed_count = 0

    while max_jobs is None or processed_count < max_jobs:
        db = session_factory()
        try:
            lock_token = str(uuid4())
            job = claim_next_revalidation_job(
                db,
                lock_token=lock_token,
                job_types=ROUTE_REVALIDATION_JOB_TYPES,
                target_types=("route",),
            )
            if job is None:
                break

            result = process_revalidation_job(
                db,
                job=job,
                lock_token=lock_token,
                provider_client=provider_client,
            )
            processed_count += 1
            if result.status == "refreshed":
                refreshed_count += 1
            elif result.status in {"no_flights", "no_active_watches"}:
                skipped_count += 1
            else:
                failed_count += 1
        finally:
            db.close()

    report = {
        "event": "watchlist_startup_refresh_worker_completed",
        "processed_job_count": processed_count,
        "refreshed_job_count": refreshed_count,
        "skipped_job_count": skipped_count,
        "failed_job_count": failed_count,
    }
    logger.info(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


def process_revalidation_job(
    db: Session,
    *,
    job: RevalidationJob,
    lock_token: str,
    provider_client: MultiSourceFlightProvider | None = None,
    now_provider=utc_now_naive,
) -> RouteRevalidationResult:
    origin_iata, destination_iata, travel_date_local = parse_route_fingerprint(job.target_fingerprint)
    result = revalidate_route(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date_local=travel_date_local,
        provider_client=provider_client,
        now_provider=now_provider,
    )
    if result.status == "provider_error":
        fail_revalidation_job(
            db,
            job_id=job.id,
            lock_token=lock_token,
            error_code="provider_error",
        )
        return result

    final_status = "done" if result.status == "refreshed" else "skipped"
    complete_revalidation_job(
        db,
        job_id=job.id,
        lock_token=lock_token,
        final_status=final_status,
    )
    return result


def revalidate_route(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date_local: Date,
    provider_client: MultiSourceFlightProvider | None = None,
    now_provider=utc_now_naive,
) -> RouteRevalidationResult:
    active_watches = list(
        db.scalars(
            select(FlightWatch)
            .where(FlightWatch.status.in_(WATCH_STATUS_TRACKABLE))
            .where(FlightWatch.origin_iata == origin_iata)
            .where(FlightWatch.destination_iata == destination_iata)
            .where(FlightWatch.travel_date_local == travel_date_local)
            .order_by(FlightWatch.created_at.asc(), FlightWatch.id.asc())
        )
    )
    if not active_watches:
        return RouteRevalidationResult(status="no_active_watches", watch_count=0, source="none")

    provider_to_use = provider_client or provider
    cached_result = _get_cached_refresh_result(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date_local=travel_date_local,
    )
    if cached_result is not None:
        if cached_result.status == "empty":
            logger.info(
                json.dumps(
                    {
                        "event": "watch_route_refresh_cache_hit_empty",
                        "origin": origin_iata,
                        "destination": destination_iata,
                        "date": travel_date_local.isoformat(),
                        "watch_count": len(active_watches),
                    },
                    ensure_ascii=False,
                )
            )
            return RouteRevalidationResult(status="no_flights", watch_count=len(active_watches), source="shared_cache")

        fetch_result = deserialize_fetch_result(cached_result.payload_json, cached_result.warnings_json)
        canonical_flight = select_canonical_refresh_flight(fetch_result.flights)
        if canonical_flight is not None:
            persisted_snapshot_count = persist_changed_snapshots_for_watches(
                db,
                watches=active_watches,
                canonical_flight=canonical_flight,
                captured_at_utc=now_provider().replace(microsecond=0),
            )
            logger.info(
                json.dumps(
                    {
                        "event": "watch_route_refresh_cache_hit",
                        "origin": origin_iata,
                        "destination": destination_iata,
                        "date": travel_date_local.isoformat(),
                        "watch_count": len(active_watches),
                        "price": float(canonical_flight.price),
                        "persisted_snapshot_count": persisted_snapshot_count,
                    },
                    ensure_ascii=False,
                )
            )
            return RouteRevalidationResult(status="refreshed", watch_count=len(active_watches), source="shared_cache")

    try:
        provider_result = provider_to_use.get_flights(
            origin_iata,
            destination_iata,
            str(travel_date_local),
        )
    except Exception as exc:
        logger.warning(
            json.dumps(
                {
                    "event": "watch_route_refresh_provider_degraded",
                    "origin": origin_iata,
                    "destination": destination_iata,
                    "date": travel_date_local.isoformat(),
                    "watch_count": len(active_watches),
                    "providers": provider_to_use.provider_ids() if hasattr(provider_to_use, "provider_ids") else ["unknown"],
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return RouteRevalidationResult(
            status="provider_error",
            watch_count=len(active_watches),
            source="provider",
            provider_error=str(exc),
        )

    flights = provider_result.flights if isinstance(provider_result, ProviderFetchResult) else provider_result
    warnings = provider_result.warnings if isinstance(provider_result, ProviderFetchResult) else []
    _persist_shared_cache_entry(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date_local=travel_date_local,
        flights=flights,
        warnings=warnings,
    )

    canonical_flight = select_canonical_refresh_flight(flights)
    if canonical_flight is None:
        return RouteRevalidationResult(status="no_flights", watch_count=len(active_watches), source="provider")

    persisted_snapshot_count = persist_changed_snapshots_for_watches(
        db,
        watches=active_watches,
        canonical_flight=canonical_flight,
        captured_at_utc=now_provider().replace(microsecond=0),
    )
    logger.info(
        json.dumps(
            {
                "event": "watch_route_refresh_completed",
                "origin": origin_iata,
                "destination": destination_iata,
                "date": travel_date_local.isoformat(),
                "watch_count": len(active_watches),
                "price": float(canonical_flight.price),
                "persisted_snapshot_count": persisted_snapshot_count,
            },
            ensure_ascii=False,
        )
    )
    return RouteRevalidationResult(status="refreshed", watch_count=len(active_watches), source="provider")

def _get_cached_refresh_result(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date_local: Date,
):
    if not WATCH_SHARED_CACHE_ENABLED:
        return None
    source_hash = build_cache_source_hash(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=str(travel_date_local),
        provider="multi",
    )
    return get_fresh_entry(
        db,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=str(travel_date_local),
        provider="multi",
        source_hash=source_hash,
    )


def _persist_shared_cache_entry(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date_local: Date,
    flights,
    warnings,
) -> None:
    if not WATCH_SHARED_CACHE_ENABLED or not flights:
        return
    payload_json, warnings_json = serialize_fetch_result(
        ProviderFetchResult(flights=flights, warnings=warnings)
    )
    category = classify_cache_result(flights=flights, warnings=warnings)
    source_hash = build_cache_source_hash(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date=str(travel_date_local),
        provider="multi",
    )
    try:
        set_cache_entry(
            db,
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            travel_date=str(travel_date_local),
            provider="multi",
            source_hash=source_hash,
            category=category,
            payload_json=payload_json,
            warnings_json=warnings_json,
        )
    except Exception:
        logger.warning(
            json.dumps(
                {
                    "event": "watch_route_refresh_cache_persist_failed",
                    "origin": origin_iata,
                    "destination": destination_iata,
                    "date": travel_date_local.isoformat(),
                },
                ensure_ascii=False,
            )
        )
