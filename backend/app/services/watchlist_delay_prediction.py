from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.live_flight_schemas import (
    LiveDelayPredictionAvailableOut,
    LiveDelayPredictionOut,
    LiveDelayPredictionUnavailableOut,
    LiveFlightLegOut,
    LiveFlightTrackingOut,
    LiveIncomingAircraftOut,
)
from app.infrastructure.db.models import (
    FlightOperationalSnapshot,
    FlightWatch,
    WatchTrackedFlightLeg,
)
from app.services.incoming_delay_prediction import (
    DelayPredictionSignal,
    Freshness,
    IncomingStatus,
    estimate_incoming_delay,
)


UnavailableStatus = Literal["insufficient_data", "not_applicable"]
UnavailableReason = Literal[
    "operational_data_missing",
    "registration_missing",
    "schedule_missing",
    "incoming_not_found",
    "already_departed",
    "flight_terminal",
]


@dataclass(frozen=True, slots=True)
class _IncomingLookup:
    target_leg: LiveFlightLegOut
    registration: str
    target_departure: datetime
    user_id: str


def attach_watchlist_delay_predictions(
    db: Session,
    tracking: LiveFlightTrackingOut,
    user_id: str,
) -> LiveFlightTrackingOut:
    legs = [
        leg.model_copy(update={"delay_prediction": _prediction_for_leg(db, tracking, leg, user_id)})
        for leg in tracking.legs
    ]
    return tracking.model_copy(update={"legs": legs})


def _prediction_for_leg(
    db: Session,
    tracking: LiveFlightTrackingOut,
    leg: LiveFlightLegOut,
    user_id: str,
) -> LiveDelayPredictionOut:
    operational = leg.operational
    if operational is None:
        return _unavailable("insufficient_data", "operational_data_missing")
    if operational.status in {"landed", "cancelled", "diverted"}:
        return _unavailable("not_applicable", "flight_terminal")
    if operational.status == "active":
        return _unavailable("not_applicable", "already_departed")
    target_departure = operational.departure.scheduled_at or leg.identity.scheduled_departure_at
    if target_departure is None:
        return _unavailable("insufficient_data", "schedule_missing")
    registration = (operational.registration or "").strip().upper()
    if not registration:
        return _unavailable("insufficient_data", "registration_missing")

    candidate = _find_incoming_aircraft(
        db,
        _IncomingLookup(
            target_leg=leg,
            registration=registration,
            target_departure=target_departure,
            user_id=user_id,
        ),
    )
    if candidate is None:
        return _unavailable("insufficient_data", "incoming_not_found")
    snapshot, incoming_leg = candidate
    scheduled_arrival = snapshot.scheduled_arrival_at
    if scheduled_arrival is None:
        return _unavailable("insufficient_data", "incoming_not_found")

    freshness: Freshness = "fresh" if snapshot.expires_at >= tracking.generated_at else "stale"
    incoming_status = _incoming_status(snapshot.status)
    estimate = estimate_incoming_delay(
        DelayPredictionSignal(
            target_scheduled_departure_at=target_departure,
            target_estimated_departure_at=operational.departure.estimated_at,
            incoming_scheduled_arrival_at=scheduled_arrival,
            incoming_estimated_arrival_at=snapshot.estimated_arrival_at,
            incoming_actual_arrival_at=snapshot.actual_arrival_at,
            incoming_status=incoming_status,
            incoming_freshness=freshness,
        )
    )
    return LiveDelayPredictionAvailableOut(
        risk=estimate.risk,
        risk_score=estimate.risk_score,
        confidence=estimate.confidence,
        predicted_delay_min_minutes=estimate.predicted_delay_min_minutes,
        predicted_delay_max_minutes=estimate.predicted_delay_max_minutes,
        turnaround_minutes=estimate.turnaround_minutes,
        factor_codes=list(estimate.factor_codes),
        incoming_aircraft=LiveIncomingAircraftOut(
            registration=registration,
            flight_number=snapshot.flight_number or incoming_leg.flight_number,
            origin_iata=incoming_leg.origin_iata,
            destination_iata=incoming_leg.destination_iata,
            status=incoming_status,
            scheduled_arrival_at=scheduled_arrival,
            estimated_arrival_at=snapshot.estimated_arrival_at,
            actual_arrival_at=snapshot.actual_arrival_at,
            observed_at=snapshot.observed_at,
            freshness=freshness,
        ),
    )


def _find_incoming_aircraft(
    db: Session,
    lookup: _IncomingLookup,
) -> tuple[FlightOperationalSnapshot, WatchTrackedFlightLeg] | None:
    row = db.execute(
        select(FlightOperationalSnapshot, WatchTrackedFlightLeg)
        .join(
            WatchTrackedFlightLeg,
            WatchTrackedFlightLeg.flight_instance_fingerprint
            == FlightOperationalSnapshot.flight_instance_fingerprint,
        )
        .join(FlightWatch, FlightWatch.id == WatchTrackedFlightLeg.watch_id)
        .where(
            FlightWatch.user_id == lookup.user_id,
            func.upper(FlightOperationalSnapshot.registration) == lookup.registration,
            FlightOperationalSnapshot.status.in_(("scheduled", "active", "landed")),
            FlightOperationalSnapshot.flight_instance_fingerprint
            != lookup.target_leg.identity.flight_instance_fingerprint,
            FlightOperationalSnapshot.scheduled_departure_at < lookup.target_departure,
            FlightOperationalSnapshot.scheduled_arrival_at
            >= lookup.target_departure - timedelta(hours=25),
            FlightOperationalSnapshot.scheduled_arrival_at <= lookup.target_departure,
            WatchTrackedFlightLeg.destination_iata == lookup.target_leg.identity.origin_iata,
        )
        .order_by(
            FlightOperationalSnapshot.scheduled_arrival_at.desc(),
            FlightOperationalSnapshot.observed_at.desc(),
        )
        .limit(1)
    ).one_or_none()
    if row is None:
        return None
    return row[0], row[1]


def _incoming_status(value: str) -> IncomingStatus:
    statuses: dict[str, IncomingStatus] = {
        "scheduled": "scheduled",
        "active": "active",
        "landed": "landed",
        "cancelled": "cancelled",
        "diverted": "diverted",
        "unknown": "unknown",
    }
    return statuses.get(value, "unknown")


def _unavailable(
    status: UnavailableStatus,
    reason: UnavailableReason,
) -> LiveDelayPredictionUnavailableOut:
    return LiveDelayPredictionUnavailableOut(status=status, reason=reason)
