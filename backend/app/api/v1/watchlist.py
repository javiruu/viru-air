import json
import logging
import os
from datetime import timedelta

from app.core.time import utc_now_naive

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

from app.core.errors import error_envelope, message_for_code
from app.core.idempotency import replay_if_exists, request_hash, store_response
from app.domain.entities import ProviderFetchResult
from app.domain.vocabulary import (
    WATCH_STATUS_DELETED,
    WATCH_STATUS_PAUSED,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import WatchCreateIn, WatchDetailOut, WatchOut, WatchRefreshBulkIn, WatchUpdateIn
from app.infrastructure.db.models import FlightWatch, PriceSnapshot, User
from app.infrastructure.db.session import get_db
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider

router = APIRouter()
provider = RyanairPublicProvider()
logger = logging.getLogger("app.watchlist")
REFRESH_COOLDOWN_SECONDS = max(0, int(os.getenv("WATCH_REFRESH_COOLDOWN_SECONDS", "60")))


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
        select(FlightWatch.id).where(
            FlightWatch.user_id == current_user.id,
            FlightWatch.origin_iata == origin_iata,
            FlightWatch.destination_iata == destination_iata,
            FlightWatch.travel_date_local == payload.travel_date_local,
        )
    )
    if existing:
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
    body = {
        "id": watch.id,
        "origin_iata": watch.origin_iata,
        "destination_iata": watch.destination_iata,
        "travel_date_local": str(watch.travel_date_local),
        "target_price": float(watch.target_price) if watch.target_price else None,
        "status": watch.status,
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
    return [
        WatchOut(
            id=w.id,
            origin_iata=w.origin_iata,
            destination_iata=w.destination_iata,
            travel_date_local=w.travel_date_local,
            target_price=float(w.target_price) if w.target_price else None,
            status=w.status,
        )
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

    latest = db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id == watch.id)
        .order_by(PriceSnapshot.captured_at_utc.desc(), PriceSnapshot.id.desc())
    )
    return WatchDetailOut(
        id=watch.id,
        origin_iata=watch.origin_iata,
        destination_iata=watch.destination_iata,
        travel_date_local=watch.travel_date_local,
        target_price=float(watch.target_price) if watch.target_price else None,
        status=watch.status,
        latest_snapshot=(
            None
            if latest is None
            else {
                "captured_at_utc": latest.captured_at_utc,
                "raw_price": float(latest.raw_price),
                "raw_currency": latest.raw_currency,
                "departure_time_local": latest.departure_time_local,
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
    watch.is_paused = payload.status == "paused"
    db.commit()
    db.refresh(watch)
    return WatchOut(
        id=watch.id,
        origin_iata=watch.origin_iata,
        destination_iata=watch.destination_iata,
        travel_date_local=watch.travel_date_local,
        target_price=float(watch.target_price) if watch.target_price else None,
        status=watch.status,
    )


@router.delete("/{watch_id}")
def delete_watch(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch or watch.status == "deleted":
        raise HTTPException(status_code=404, detail="watch_not_found")
    watch.status = WATCH_STATUS_DELETED
    watch.is_paused = True
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
    if watch.is_paused or watch.status == WATCH_STATUS_PAUSED:
        raise HTTPException(status_code=409, detail="watch_paused")

    if REFRESH_COOLDOWN_SECONDS > 0:
        latest_snapshot = db.scalar(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == watch.id)
            .order_by(PriceSnapshot.captured_at_utc.desc(), PriceSnapshot.id.desc())
        )
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

    try:
        provider_result = provider.get_flights(
            watch.origin_iata, watch.destination_iata, str(watch.travel_date_local)
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="ryanair_unavailable") from exc

    flights = provider_result.flights if isinstance(provider_result, ProviderFetchResult) else provider_result
    if not flights:
        raise HTTPException(status_code=404, detail="no_flights_found")
    for flight in flights:
        snapshot = PriceSnapshot(
            watch_id=watch.id,
            captured_at_utc=utc_now_naive(),
            departure_time_local=flight.departure_time_local,
            raw_price=flight.price,
            raw_currency=flight.currency,
            provider=flight.source,
        )
        db.add(snapshot)
    db.commit()
    return None
