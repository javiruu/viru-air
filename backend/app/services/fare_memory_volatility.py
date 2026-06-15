from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightPriceObservation, FlightWatch, PriceSnapshot

_MINIMUM_VOLATILITY_OBSERVATIONS = 3
_RECENT_DIRECTION_WINDOW = 3


@dataclass(slots=True)
class _ObservedPoint:
    observed_at: dt.datetime
    price_amount: float


def build_offer_volatility_report(
    db: Session,
    *,
    offer_id: str,
    minimum_observations: int = _MINIMUM_VOLATILITY_OBSERVATIONS,
) -> dict[str, Any]:
    observations = db.scalars(
        select(FlightPriceObservation)
        .where(FlightPriceObservation.offer_id == offer_id)
        .where(FlightPriceObservation.price_amount.is_not(None))
        .order_by(FlightPriceObservation.observed_at.asc(), FlightPriceObservation.id.asc())
    ).all()
    points = [
        _ObservedPoint(
            observed_at=observation.observed_at,
            price_amount=float(observation.price_amount),
        )
        for observation in observations
    ]
    report = _build_volatility_report_from_points(
        points,
        subject_key=offer_id,
        subject_type="offer",
        minimum_observations=minimum_observations,
    )
    if observations:
        report["provider"] = observations[-1].provider
        report["currency"] = observations[-1].currency
    return report


def build_route_volatility_report(
    db: Session,
    *,
    origin_iata: str,
    destination_iata: str,
    travel_date_local: dt.date,
    minimum_observations: int = _MINIMUM_VOLATILITY_OBSERVATIONS,
) -> dict[str, Any]:
    snapshots = db.execute(
        select(PriceSnapshot, FlightWatch)
        .join(FlightWatch, PriceSnapshot.watch_id == FlightWatch.id)
        .where(FlightWatch.origin_iata == origin_iata.upper())
        .where(FlightWatch.destination_iata == destination_iata.upper())
        .where(FlightWatch.travel_date_local == travel_date_local)
        .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
    ).all()
    points = [
        _ObservedPoint(
            observed_at=snapshot.captured_at_utc,
            price_amount=float(snapshot.raw_price),
        )
        for snapshot, _watch in snapshots
    ]
    subject_key = f"route:{origin_iata.upper()}:{destination_iata.upper()}:{travel_date_local.isoformat()}"
    report = _build_volatility_report_from_points(
        points,
        subject_key=subject_key,
        subject_type="route",
        minimum_observations=minimum_observations,
    )
    if snapshots:
        report["provider"] = snapshots[-1][0].provider
        report["currency"] = snapshots[-1][0].raw_currency
        report["watch_count"] = len({watch.id for _snapshot, watch in snapshots})
    return report


def _build_volatility_report_from_points(
    points: Sequence[_ObservedPoint],
    *,
    subject_key: str,
    subject_type: str,
    minimum_observations: int,
) -> dict[str, Any]:
    ordered_points = sorted(points, key=lambda point: (point.observed_at, point.price_amount))
    observation_count = len(ordered_points)
    sufficient_observations = observation_count >= max(1, int(minimum_observations))

    if observation_count == 0:
        return _empty_volatility_report(
            subject_key=subject_key,
            subject_type=subject_type,
            observation_count=0,
            sufficient_observations=False,
        )

    if observation_count == 1:
        return _empty_volatility_report(
            subject_key=subject_key,
            subject_type=subject_type,
            observation_count=1,
            sufficient_observations=False,
            first_observed_at=ordered_points[0].observed_at,
            last_observed_at=ordered_points[0].observed_at,
        )

    deltas_abs: list[float] = []
    deltas_pct: list[float] = []
    change_timestamps: list[dt.datetime] = []
    change_directions: list[str] = []

    for previous, current in zip(ordered_points, ordered_points[1:]):
        delta_abs = round(current.price_amount - previous.price_amount, 2)
        deltas_abs.append(abs(delta_abs))
        if previous.price_amount != 0:
            deltas_pct.append(abs(delta_abs / previous.price_amount))
        if abs(delta_abs) > 0.0001:
            change_timestamps.append(current.observed_at)
            change_directions.append("up" if delta_abs > 0 else "down")

    total_window_seconds = max(
        1.0,
        (ordered_points[-1].observed_at - ordered_points[0].observed_at).total_seconds(),
    )
    total_window_days = total_window_seconds / 86400.0
    changes_count = len(change_timestamps)
    changes_per_day = round(changes_count / total_window_days, 4)
    average_delta_abs = round(sum(deltas_abs) / len(deltas_abs), 2)
    max_delta_abs = round(max(deltas_abs), 2)

    average_time_between_changes_seconds: int | None = None
    if len(change_timestamps) >= 2:
        intervals = [
            max(0, int((current - previous).total_seconds()))
            for previous, current in zip(change_timestamps, change_timestamps[1:])
        ]
        average_time_between_changes_seconds = int(sum(intervals) / len(intervals))

    dominant_direction_recent = _dominant_direction_recent(change_directions, sufficient_observations=sufficient_observations)
    average_delta_pct = round(sum(deltas_pct) / len(deltas_pct), 4) if deltas_pct else None
    volatility_score = _build_volatility_score(
        sufficient_observations=sufficient_observations,
        changes_per_day=changes_per_day,
        average_delta_pct=average_delta_pct,
        changes_count=changes_count,
    )

    return {
        "subject_type": subject_type,
        "subject_key": subject_key,
        "observation_count": observation_count,
        "sufficient_observations": sufficient_observations,
        "status": "ok" if sufficient_observations else "insufficient_data",
        "changes_count": changes_count,
        "changes_per_day": changes_per_day,
        "average_delta_abs": average_delta_abs,
        "max_delta_abs": max_delta_abs,
        "average_time_between_changes_seconds": average_time_between_changes_seconds,
        "dominant_direction_recent": dominant_direction_recent,
        "average_delta_pct": average_delta_pct,
        "volatility_score": volatility_score,
        "first_observed_at": ordered_points[0].observed_at.isoformat(),
        "last_observed_at": ordered_points[-1].observed_at.isoformat(),
    }


def _empty_volatility_report(
    *,
    subject_key: str,
    subject_type: str,
    observation_count: int,
    sufficient_observations: bool,
    first_observed_at: dt.datetime | None = None,
    last_observed_at: dt.datetime | None = None,
) -> dict[str, Any]:
    return {
        "subject_type": subject_type,
        "subject_key": subject_key,
        "observation_count": observation_count,
        "sufficient_observations": sufficient_observations,
        "status": "insufficient_data",
        "changes_count": 0,
        "changes_per_day": 0.0,
        "average_delta_abs": 0.0,
        "max_delta_abs": 0.0,
        "average_time_between_changes_seconds": None,
        "dominant_direction_recent": "insufficient_data",
        "average_delta_pct": None,
        "volatility_score": None,
        "first_observed_at": first_observed_at.isoformat() if first_observed_at is not None else None,
        "last_observed_at": last_observed_at.isoformat() if last_observed_at is not None else None,
    }


def _dominant_direction_recent(change_directions: Sequence[str], *, sufficient_observations: bool) -> str:
    if not sufficient_observations:
        return "insufficient_data"
    if not change_directions:
        return "flat"

    recent = list(change_directions[-_RECENT_DIRECTION_WINDOW:])
    up_count = recent.count("up")
    down_count = recent.count("down")
    if up_count and not down_count:
        return "up"
    if down_count and not up_count:
        return "down"
    if up_count == down_count:
        return "mixed"
    return "up" if up_count > down_count else "down"


def _build_volatility_score(
    *,
    sufficient_observations: bool,
    changes_per_day: float,
    average_delta_pct: float | None,
    changes_count: int,
) -> float | None:
    if not sufficient_observations:
        return None

    frequency_component = min(1.0, changes_per_day / 6.0)
    magnitude_component = min(1.0, (average_delta_pct or 0.0) / 0.25)
    confidence_component = min(1.0, changes_count / 4.0)
    score = (frequency_component * 0.45) + (magnitude_component * 0.35) + (confidence_component * 0.20)
    return round(score, 4)
