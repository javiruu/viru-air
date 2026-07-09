import json
import logging
import os
from datetime import date as Date, timedelta
from uuid import uuid4

from app.core.time import utc_now_naive

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from app.core.errors import error_envelope, message_for_code
from app.core.idempotency import replay_if_exists, request_hash, store_response
from app.domain.vocabulary import (
    WATCH_STATUS_ACTIVE,
    WATCH_STATUS_DELETED,
    WATCH_STATUS_PAUSED,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import (
    WatchCreateIn,
    WatchDeleteBulkIn,
    WatchDetailOut,
    WatchOut,
    WatchRefreshBulkIn,
    WatchStatusBulkIn,
    WatchUpdateIn,
)
from app.infrastructure.db.models import FlightWatch, PriceSnapshot, User
from app.infrastructure.db.session import get_db
from app.infrastructure.providers.flight_provider import MultiSourceFlightProvider
from app.services.watchlist_snapshots import canonicalize_snapshot_rows
from app.services.fare_memory_config import (
    FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE,
    FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED,
)
from app.services.revalidation_jobs import (
    claim_revalidation_job,
    enqueue_revalidation_job,
    find_active_revalidation_job,
)
from app.services.watchlist_backfill import find_backfill_observations_for_watch, persist_backfill_snapshots_for_watch
from app.services.watchlist_revalidation import (
    WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS,
    process_revalidation_job,
    route_fingerprint,
)
from app.services.watchlist_refresh_policy import evaluate_route_freshness, latest_snapshot_by_watch_ids

router = APIRouter()
provider = MultiSourceFlightProvider()
logger = logging.getLogger("app.watchlist")
REFRESH_COOLDOWN_SECONDS = max(0, int(os.getenv("WATCH_REFRESH_COOLDOWN_SECONDS", "60")))

WatchRouteKey = tuple[str, str, Date]


def _watch_route_key(watch: FlightWatch) -> WatchRouteKey:
    return (watch.origin_iata, watch.destination_iata, watch.travel_date_local)


def _watch_revalidation_target_fingerprint(watch: FlightWatch) -> str:
    return route_fingerprint(watch.origin_iata, watch.destination_iata, watch.travel_date_local)


def _manual_revalidation_retry_after_seconds() -> int:
    return max(1, int(60 / max(1, FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE)))


def _watch_out(watch: FlightWatch, watchers_count: int = 0) -> WatchOut:
    return WatchOut(
        id=watch.id,
        origin_iata=watch.origin_iata,
        destination_iata=watch.destination_iata,
        travel_date_local=watch.travel_date_local,
        target_price=float(watch.target_price) if watch.target_price else None,
        status=watch.status,
        watchers_count=watchers_count,
        group_id=watch.group_id,
    )


def _count_watchers_by_route(
    db: Session,
    route_keys: set[WatchRouteKey],
    *,
    current_user_id: str,
) -> dict[WatchRouteKey, int]:
    if not route_keys:
        return {}

    origins = {origin for origin, _, _ in route_keys}
    destinations = {destination for _, destination, _ in route_keys}
    travel_dates = {travel_date for _, _, travel_date in route_keys}

    rows = db.execute(
        select(
            FlightWatch.origin_iata,
            FlightWatch.destination_iata,
            FlightWatch.travel_date_local,
            FlightWatch.user_id,
        ).where(
            FlightWatch.status != WATCH_STATUS_DELETED,
            FlightWatch.origin_iata.in_(origins),
            FlightWatch.destination_iata.in_(destinations),
            FlightWatch.travel_date_local.in_(travel_dates),
        )
    ).all()

    users_by_route: dict[WatchRouteKey, set[str]] = {}
    for origin_iata, destination_iata, travel_date_local, user_id in rows:
        key = (origin_iata, destination_iata, travel_date_local)
        if key not in route_keys:
            continue
        users_by_route.setdefault(key, set()).add(user_id)

    return {key: max(0, len(user_ids - {current_user_id})) for key, user_ids in users_by_route.items()}


@router.post("", response_model=WatchOut)
def create_watch(
    payload: WatchCreateIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WatchOut:
    req_hash = request_hash(payload.model_dump(mode="json"))
    endpoint = "POST:/api/v1/watchlist"
    replay = replay_if_exists(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
    )
    if replay:
        status_code, body = replay
        response = JSONResponse(status_code=status_code, content=body)
        response.headers["x-idempotency-replayed"] = "true"
        return response

    origin_iata = payload.origin_iata.upper()
    destination_iata = payload.destination_iata.upper()

    if origin_iata == destination_iata:
        raise HTTPException(status_code=400, detail="origin_equals_destination")

    existing = db.scalar(
        select(FlightWatch).where(
            FlightWatch.user_id == current_user.id,
            FlightWatch.origin_iata == origin_iata,
            FlightWatch.destination_iata == destination_iata,
            FlightWatch.travel_date_local == payload.travel_date_local,
        )
    )
    if existing:
        if existing.status == WATCH_STATUS_DELETED:
            existing.status = WATCH_STATUS_ACTIVE
            existing.target_price = payload.target_price
            db.commit()
            db.refresh(existing)
            watchers_count = _count_watchers_by_route(
                db,
                {_watch_route_key(existing)},
                current_user_id=current_user.id,
            ).get(
                _watch_route_key(existing), 0
            )
            return _watch_out(existing, watchers_count)
        raise HTTPException(status_code=409, detail="watch_already_exists")

    watch = FlightWatch(
        user_id=current_user.id,
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        travel_date_local=payload.travel_date_local,
        target_price=payload.target_price,
    )
    db.add(watch)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="watch_already_exists") from exc
    db.refresh(watch)
    if FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED:
        try:
            backfill_observations = find_backfill_observations_for_watch(db, watch)
            persist_backfill_snapshots_for_watch(db, watch, backfill_observations)
        except Exception:
            db.rollback()
            logger.exception(
                "watchlist_backfill_failed",
                extra={
                    "watch_id": watch.id,
                    "origin_iata": watch.origin_iata,
                    "destination_iata": watch.destination_iata,
                    "travel_date_local": str(watch.travel_date_local),
                },
            )
    watchers_count = _count_watchers_by_route(
        db,
        {_watch_route_key(watch)},
        current_user_id=current_user.id,
    ).get(_watch_route_key(watch), 0)
    body = {
        "id": watch.id,
        "origin_iata": watch.origin_iata,
        "destination_iata": watch.destination_iata,
        "travel_date_local": str(watch.travel_date_local),
        "target_price": float(watch.target_price) if watch.target_price else None,
        "status": watch.status,
        "watchers_count": watchers_count,
        "group_id": watch.group_id,
    }
    store_response(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
        response_status=200,
        response_body=body,
    )
    return WatchOut(**body)


@router.get("", response_model=list[WatchOut])
def list_watches(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[WatchOut]:
    watches = list(
        db.scalars(
            select(FlightWatch)
            .where(FlightWatch.user_id == current_user.id, FlightWatch.status != WATCH_STATUS_DELETED)
            .order_by(FlightWatch.created_at.desc(), FlightWatch.id.desc())
        )
    )
    route_keys = {_watch_route_key(watch) for watch in watches}
    watchers_count_by_route = _count_watchers_by_route(
        db,
        route_keys,
        current_user_id=current_user.id,
    )
    return [
        _watch_out(w, watchers_count_by_route.get(_watch_route_key(w), 0))
        for w in watches
    ]


@router.post("/refresh-bulk")
def refresh_watch_bulk(
    payload: WatchRefreshBulkIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    deduped_watch_ids = list(dict.fromkeys(payload.watch_ids))
    refreshed: list[str] = []
    failed: list[dict[str, str]] = []
    for watch_id in deduped_watch_ids:
        try:
            _refresh_watch_now(db=db, watch_id=watch_id, current_user=current_user)
            refreshed.append(watch_id)
        except HTTPException as exc:
            failed.append({"watch_id": watch_id, "code": str(exc.detail)})
    return {"status": "ok", "requested": len(deduped_watch_ids), "refreshed": refreshed, "failed": failed}


@router.post("/status-bulk")
def update_watch_status_bulk(
    payload: WatchStatusBulkIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    deduped_watch_ids = list(dict.fromkeys(payload.watch_ids))
    updated_ids: list[str] = []
    failed: list[dict[str, str]] = []
    for watch_id in deduped_watch_ids:
        watch = db.scalar(
            select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
        )
        if not watch or watch.status == WATCH_STATUS_DELETED:
            failed.append({"watch_id": watch_id, "code": "watch_not_found"})
            continue
        watch.status = payload.status
        updated_ids.append(watch_id)
    db.commit()
    return {
        "status": "ok",
        "requested": len(deduped_watch_ids),
        "updated_ids": updated_ids,
        "failed": failed,
    }


@router.post("/delete-bulk")
def delete_watch_bulk(
    payload: WatchDeleteBulkIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    deduped_watch_ids = list(dict.fromkeys(payload.watch_ids))
    deleted_ids: list[str] = []
    failed: list[dict[str, str]] = []
    for watch_id in deduped_watch_ids:
        watch = db.scalar(
            select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
        )
        if not watch or watch.status == WATCH_STATUS_DELETED:
            failed.append({"watch_id": watch_id, "code": "watch_not_found"})
            continue
        watch.status = WATCH_STATUS_DELETED
        deleted_ids.append(watch_id)
    db.commit()
    return {
        "status": "ok",
        "requested": len(deduped_watch_ids),
        "deleted_ids": deleted_ids,
        "failed": failed,
    }


@router.get("/{watch_id}", response_model=WatchDetailOut)
def get_watch_detail(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WatchDetailOut:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch or watch.status == WATCH_STATUS_DELETED:
        raise HTTPException(status_code=404, detail="watch_not_found")

    snapshot_rows = list(
        db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == watch.id)
            .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
        )
    )
    canonical_snapshots = sorted(
        canonicalize_snapshot_rows(snapshot_rows),
        key=lambda snapshot: snapshot.captured_at_utc,
    )
    latest = canonical_snapshots[-1] if canonical_snapshots else None
    watchers_count = _count_watchers_by_route(
        db,
        {_watch_route_key(watch)},
        current_user_id=current_user.id,
    ).get(_watch_route_key(watch), 0)
    return WatchDetailOut(
        id=watch.id,
        origin_iata=watch.origin_iata,
        destination_iata=watch.destination_iata,
        travel_date_local=watch.travel_date_local,
        target_price=float(watch.target_price) if watch.target_price else None,
        status=watch.status,
        watchers_count=watchers_count,
        group_id=watch.group_id,
        latest_snapshot=(
            None
            if latest is None
            else {
                "captured_at_utc": latest.captured_at_utc,
                "raw_price": latest.raw_price,
                "raw_currency": latest.raw_currency,
                "departure_time_local": latest.departure_time_local,
                "provider": latest.provider,
            }
        ),
    )


@router.put("/{watch_id}", response_model=WatchOut)
def update_watch(
    watch_id: str,
    payload: WatchUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WatchOut:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch or watch.status == WATCH_STATUS_DELETED:
        raise HTTPException(status_code=404, detail="watch_not_found")

    watch.status = payload.status
    if payload.target_price is not None:
        watch.target_price = payload.target_price if payload.target_price > 0 else None
    db.commit()
    db.refresh(watch)
    watchers_count = _count_watchers_by_route(
        db,
        {_watch_route_key(watch)},
        current_user_id=current_user.id,
    ).get(_watch_route_key(watch), 0)
    return _watch_out(watch, watchers_count)


@router.delete("/{watch_id}")
def delete_watch(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch or watch.status == WATCH_STATUS_DELETED:
        raise HTTPException(status_code=404, detail="watch_not_found")
    watch.status = WATCH_STATUS_DELETED
    db.commit()
    return {"status": "ok"}


@router.post("/{watch_id}/refresh-now")
def refresh_watch(
    watch_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    endpoint = f"POST:/api/v1/watchlist/{watch_id}/refresh-now"
    req_hash = request_hash({})
    replay = replay_if_exists(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
    )
    if replay:
        status_code, body = replay
        response = JSONResponse(status_code=status_code, content=body)
        response.headers["x-idempotency-replayed"] = "true"
        return response

    refresh_result = _refresh_watch_now(db=db, watch_id=watch_id, current_user=current_user)
    if isinstance(refresh_result, JSONResponse):
        if idempotency_key:
            response_body = json.loads(refresh_result.body.decode("utf-8"))
            store_response(
                db,
                user_id=current_user.id,
                endpoint=endpoint,
                idempotency_key=idempotency_key,
                req_hash=req_hash,
                response_status=refresh_result.status_code,
                response_body=response_body,
            )
        return refresh_result
    body = {"status": "queued", "watch_id": watch_id}
    store_response(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        req_hash=req_hash,
        response_status=200,
        response_body=body,
    )
    return body


def _refresh_watch_now(db: Session, watch_id: str, current_user: User) -> JSONResponse | None:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch:
        raise HTTPException(status_code=404, detail="watch_not_found")
    if watch.status == WATCH_STATUS_DELETED:
        raise HTTPException(status_code=404, detail="watch_not_found")
    if watch.status == WATCH_STATUS_PAUSED:
        raise HTTPException(status_code=409, detail="watch_paused")

    latest_snapshot = latest_snapshot_by_watch_ids(db, [watch.id]).get(watch.id)
    route_freshness = evaluate_route_freshness(
        watches=[watch],
        latest_snapshot_by_watch={watch.id: latest_snapshot} if latest_snapshot is not None else {},
        now=utc_now_naive(),
        max_age_seconds=WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS,
    )

    if REFRESH_COOLDOWN_SECONDS > 0:
        if latest_snapshot:
            current_utc = utc_now_naive()
            earliest_next_refresh = latest_snapshot.captured_at_utc + timedelta(seconds=REFRESH_COOLDOWN_SECONDS)
            if earliest_next_refresh > current_utc:
                retry_after = max(1, int((earliest_next_refresh - current_utc).total_seconds()))
                logger.info(
                    json.dumps(
                        {
                            "event": "watch_refresh_denied_cooldown",
                            "user_id": current_user.id,
                            "watch_id": watch.id,
                            "retry_after_sec": retry_after,
                            "cooldown_sec": REFRESH_COOLDOWN_SECONDS,
                        },
                        ensure_ascii=False,
                    )
                )
                response = JSONResponse(
                    status_code=429,
                    content=error_envelope(
                        status=429,
                        code="refresh_cooldown_active",
                        message=message_for_code("refresh_cooldown_active", fallback="Refresh cooldown active."),
                        details=[],
                        retry_after_sec=retry_after,
                    ),
                )
                response.headers["Retry-After"] = str(retry_after)
                return response

    active_job = find_active_revalidation_job(
        db,
        target_type="route",
        target_fingerprint=_watch_revalidation_target_fingerprint(watch),
        provider="multi",
    )
    if active_job is not None:
        retry_after = _manual_revalidation_retry_after_seconds()
        logger.info(
            json.dumps(
                {
                    "event": "watch_refresh_revalidation_deduped",
                    "user_id": current_user.id,
                    "watch_id": watch.id,
                    "job_id": active_job.id,
                    "retry_after_sec": retry_after,
                },
                ensure_ascii=False,
            )
        )
        response = JSONResponse(
            status_code=429,
            content=error_envelope(
                status=429,
                code="revalidation_already_in_progress",
                message=message_for_code("revalidation_already_in_progress"),
                details=[{"job_id": active_job.id}],
                retry_after_sec=retry_after,
            ),
        )
        response.headers["Retry-After"] = str(retry_after)
        return response

    revalidation_job, created = enqueue_revalidation_job(
        db,
        job_type="manual",
        target_type="route",
        target_fingerprint=_watch_revalidation_target_fingerprint(watch),
        provider="multi",
        priority=20,
        payload={
            "watch_id": watch.id,
            "user_id": current_user.id,
            "freshness_state": route_freshness.state,
            "oldest_snapshot_age_seconds": route_freshness.oldest_snapshot_age_seconds,
        },
    )
    if not created:
        retry_after = _manual_revalidation_retry_after_seconds()
        response = JSONResponse(
            status_code=429,
            content=error_envelope(
                status=429,
                code="revalidation_already_in_progress",
                message=message_for_code("revalidation_already_in_progress"),
                details=[{"job_id": revalidation_job.id}],
                retry_after_sec=retry_after,
            ),
        )
        response.headers["Retry-After"] = str(retry_after)
        return response

    lock_token = str(uuid4())
    claimed_job = claim_revalidation_job(db, job_id=revalidation_job.id, lock_token=lock_token)
    if claimed_job is None:
        retry_after = _manual_revalidation_retry_after_seconds()
        response = JSONResponse(
            status_code=429,
            content=error_envelope(
                status=429,
                code="revalidation_already_in_progress",
                message=message_for_code("revalidation_already_in_progress"),
                details=[{"job_id": revalidation_job.id}],
                retry_after_sec=retry_after,
            ),
        )
        response.headers["Retry-After"] = str(retry_after)
        return response

    result = process_revalidation_job(
        db,
        job=claimed_job,
        lock_token=lock_token,
        provider_client=provider,
        now_provider=utc_now_naive,
    )
    if result.status == "provider_error":
        return JSONResponse(
            status_code=200,
            content={
                "status": "queued",
                "watch_id": watch.id,
                "stale_data": True,
                "provider_status": "degraded",
            },
        )

    if result.status in {"no_flights", "no_active_watches"}:
        return JSONResponse(
            status_code=200,
            content={"status": "no_flights", "watch_id": watch.id},
        )
    return None
