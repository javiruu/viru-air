from collections import defaultdict
from datetime import date as Date
from statistics import pstdev

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import SnapshotBatchIn, SnapshotBatchOut, SnapshotOut
from app.infrastructure.db.models import FlightWatch, PriceSnapshot, User
from app.infrastructure.db.session import get_db

router = APIRouter()


@router.get("/history", response_model=list[SnapshotOut])
def history(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SnapshotOut]:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch:
        return []

    rows = list(
        db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == watch_id)
            .order_by(PriceSnapshot.captured_at_utc.desc(), PriceSnapshot.id.desc())
        )
    )
    return [
        SnapshotOut(
            captured_at_utc=r.captured_at_utc,
            raw_price=float(r.raw_price),
            raw_currency=r.raw_currency,
            departure_time_local=r.departure_time_local,
        )
        for r in rows
    ]


@router.post("/history/batch", response_model=list[SnapshotBatchOut])
def history_batch(
    payload: SnapshotBatchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SnapshotBatchOut]:
    watch_ids = [watch_id for watch_id in payload.watch_ids if watch_id]
    if not watch_ids:
        return []

    deduped_watch_ids = list(dict.fromkeys(watch_ids))

    allowed_watch_ids = set(
        db.scalars(
            select(FlightWatch.id).where(
                FlightWatch.user_id == current_user.id,
                FlightWatch.id.in_(deduped_watch_ids),
            )
        )
    )
    if not allowed_watch_ids:
        return []

    count_stmt = select(func.count(PriceSnapshot.id)).where(PriceSnapshot.watch_id.in_(allowed_watch_ids))
    if payload.captured_since_utc is not None:
        count_stmt = count_stmt.where(PriceSnapshot.captured_at_utc >= payload.captured_since_utc)

    total_rows = int(db.scalar(count_stmt) or 0)
    if total_rows > payload.max_rows:
        raise HTTPException(status_code=413, detail="batch_history_too_large")

    rows_stmt = select(PriceSnapshot).where(PriceSnapshot.watch_id.in_(allowed_watch_ids))
    if payload.captured_since_utc is not None:
        rows_stmt = rows_stmt.where(PriceSnapshot.captured_at_utc >= payload.captured_since_utc)

    rows = list(
        db.scalars(
            rows_stmt.order_by(
                PriceSnapshot.watch_id.asc(),
                PriceSnapshot.captured_at_utc.desc(),
                PriceSnapshot.id.desc(),
            )
        )
    )
    return [
        SnapshotBatchOut(
            watch_id=r.watch_id,
            captured_at_utc=r.captured_at_utc,
            raw_price=float(r.raw_price),
            raw_currency=r.raw_currency,
            departure_time_local=r.departure_time_local,
        )
        for r in rows
    ]


@router.get("/summary")
def summary(
    watch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, float | int | str | None]:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch:
        raise HTTPException(status_code=404, detail="watch_not_found")

    rows = list(
        db.scalars(
            select(PriceSnapshot)
            .where(PriceSnapshot.watch_id == watch_id)
            .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
        )
    )
    if not rows:
        return {
            "watch_id": watch_id,
            "count": 0,
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "latest_price": None,
            "delta_pct": None,
        }

    prices = [float(row.raw_price) for row in rows]
    first = prices[0]
    latest = prices[-1]
    delta_pct = None if first == 0 else round(((latest - first) / first) * 100.0, 2)
    return {
        "watch_id": watch_id,
        "count": len(prices),
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": round(sum(prices) / len(prices), 2),
        "latest_price": latest,
        "delta_pct": delta_pct,
    }


@router.get("/calendar")
def calendar(
    watch_id: str,
    from_: Date | None = Query(default=None, alias="from"),
    to: Date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | list[dict[str, str | float | int | bool | None]]]:
    watch = db.scalar(
        select(FlightWatch).where(FlightWatch.id == watch_id, FlightWatch.user_id == current_user.id)
    )
    if not watch:
        raise HTTPException(status_code=404, detail="watch_not_found")

    stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id == watch_id)
        .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
    )
    if from_ is not None:
        stmt = stmt.where(func.date(PriceSnapshot.captured_at_utc) >= from_)
    if to is not None:
        stmt = stmt.where(func.date(PriceSnapshot.captured_at_utc) <= to)

    rows = list(db.scalars(stmt))
    if not rows:
        return {"watch_id": watch_id, "currency": "EUR", "days": []}

    by_day: dict[Date, list[PriceSnapshot]] = defaultdict(list)
    for row in rows:
        by_day[row.captured_at_utc.date()].append(row)

    day_min_values: list[float] = []
    day_max_values: list[float] = []
    day_stats: list[dict[str, str | float | int | bool | None]] = []
    for day in sorted(by_day.keys()):
        snapshots = by_day[day]
        prices = [float(item.raw_price) for item in snapshots]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = round(sum(prices) / len(prices), 2)
        day_min_values.append(min_price)
        day_max_values.append(max_price)
        stale_count = sum(1 for item in snapshots if item.is_stale)
        freshness_state: str | None
        if stale_count == 0:
            freshness_state = "fresh"
        elif stale_count == len(snapshots):
            freshness_state = "stale"
        else:
            freshness_state = "mixed"
        day_stats.append(
            {
                "date": day.isoformat(),
                "min_price": min_price,
                "max_price": max_price,
                "avg_price": avg_price,
                "snapshot_count": len(snapshots),
                "is_daily_min": False,
                "is_daily_max": False,
                "freshness_state": freshness_state,
            }
        )

    overall_day_min = min(day_min_values)
    overall_day_max = max(day_max_values)
    for day in day_stats:
        day["is_daily_min"] = day["min_price"] == overall_day_min
        day["is_daily_max"] = day["max_price"] == overall_day_max

    return {"watch_id": watch_id, "currency": rows[-1].raw_currency, "days": day_stats}


def _volatility_hint(prices: list[float]) -> str:
    if len(prices) < 3:
        return "insufficient_data"
    avg_price = sum(prices) / len(prices)
    if avg_price <= 0:
        return "insufficient_data"
    coefficient = pstdev(prices) / avg_price
    if coefficient < 0.03:
        return "low"
    if coefficient < 0.08:
        return "medium"
    return "high"


@router.get("/compare")
def compare(
    watch_ids: str,
    from_: Date | None = Query(default=None, alias="from"),
    to: Date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | list[dict[str, str | float | int | None | list[dict[str, str | float | int]]]]]:
    requested_ids = [item.strip() for item in watch_ids.split(",") if item.strip()]
    unique_ids = list(dict.fromkeys(requested_ids))
    if len(unique_ids) < 2:
        raise HTTPException(status_code=400, detail="compare_requires_two_to_four_watches")
    if len(unique_ids) > 4:
        raise HTTPException(status_code=400, detail="compare_watch_limit_exceeded")

    watches = list(
        db.scalars(
            select(FlightWatch).where(
                FlightWatch.id.in_(unique_ids),
                FlightWatch.user_id == current_user.id,
            )
        )
    )
    watch_by_id = {watch.id: watch for watch in watches}
    if len(watch_by_id) != len(unique_ids):
        raise HTTPException(status_code=403, detail="compare_contains_foreign_or_missing_watch")

    rows_stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id.in_(unique_ids))
        .order_by(PriceSnapshot.watch_id.asc(), PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
    )
    if from_ is not None:
        rows_stmt = rows_stmt.where(func.date(PriceSnapshot.captured_at_utc) >= from_)
    if to is not None:
        rows_stmt = rows_stmt.where(func.date(PriceSnapshot.captured_at_utc) <= to)
    rows = list(db.scalars(rows_stmt))

    by_watch: dict[str, list[PriceSnapshot]] = defaultdict(list)
    for row in rows:
        by_watch[row.watch_id].append(row)

    currencies = {snapshots[-1].raw_currency for snapshots in by_watch.values() if snapshots}
    currency_mode = "mixed" if len(currencies) > 1 else "single"

    watch_payload: list[dict[str, str | float | int | None]] = []
    points_payload: list[dict[str, str | list[dict[str, str | float | int]]]] = []
    for watch_id in unique_ids:
        watch = watch_by_id[watch_id]
        snapshots = by_watch.get(watch_id, [])
        prices = [float(item.raw_price) for item in snapshots]
        currency = snapshots[-1].raw_currency if snapshots else "EUR"
        watch_payload.append(
            {
                "watch_id": watch_id,
                "route": f"{watch.origin_iata}->{watch.destination_iata}",
                "travel_date": watch.travel_date_local.isoformat(),
                "currency": currency,
                "latest_price": prices[-1] if prices else None,
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
                "snapshot_count": len(prices),
                "volatility_hint": _volatility_hint(prices),
            }
        )

        by_day: dict[str, list[float]] = defaultdict(list)
        for row in snapshots:
            by_day[row.captured_at_utc.date().isoformat()].append(float(row.raw_price))
        points_payload.append(
            {
                "watch_id": watch_id,
                "points": [
                    {
                        "date": day,
                        "avg_price": round(sum(day_prices) / len(day_prices), 2),
                        "snapshot_count": len(day_prices),
                        "currency": currency,
                    }
                    for day, day_prices in sorted(by_day.items())
                ],
            }
        )

    return {"currency_mode": currency_mode, "watches": watch_payload, "points": points_payload}
