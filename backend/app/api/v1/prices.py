from fastapi import APIRouter, Depends, HTTPException
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
