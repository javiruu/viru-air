from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


DelayRisk = Literal["low", "elevated", "high"]
DelayConfidence = Literal["low", "medium", "high"]
DelayFactorCode = Literal[
    "incoming_running_late",
    "tight_turnaround",
    "incoming_airborne",
    "official_delay_signal",
    "incoming_landed",
    "healthy_turnaround",
    "stale_observation",
]
IncomingStatus = Literal[
    "scheduled",
    "active",
    "landed",
    "cancelled",
    "diverted",
    "unknown",
]
Freshness = Literal["fresh", "stale"]

MINIMUM_TURNAROUND_MINUTES = 45


@dataclass(frozen=True, slots=True)
class DelayPredictionSignal:
    target_scheduled_departure_at: datetime
    target_estimated_departure_at: datetime | None
    incoming_scheduled_arrival_at: datetime
    incoming_estimated_arrival_at: datetime | None
    incoming_actual_arrival_at: datetime | None
    incoming_status: IncomingStatus
    incoming_freshness: Freshness


@dataclass(frozen=True, slots=True)
class IncomingDelayEstimate:
    risk: DelayRisk
    risk_score: int
    confidence: DelayConfidence
    predicted_delay_min_minutes: int
    predicted_delay_max_minutes: int
    turnaround_minutes: int
    factor_codes: tuple[DelayFactorCode, ...]


def estimate_incoming_delay(signal: DelayPredictionSignal) -> IncomingDelayEstimate:
    incoming_arrival_at = (
        signal.incoming_actual_arrival_at
        or signal.incoming_estimated_arrival_at
        or signal.incoming_scheduled_arrival_at
    )
    turnaround_minutes = round(
        (signal.target_scheduled_departure_at - incoming_arrival_at).total_seconds() / 60
    )
    incoming_delay_minutes = max(
        0,
        round((incoming_arrival_at - signal.incoming_scheduled_arrival_at).total_seconds() / 60),
    )
    official_delay_minutes = (
        max(
            0,
            round(
                (
                    signal.target_estimated_departure_at - signal.target_scheduled_departure_at
                ).total_seconds()
                / 60
            ),
        )
        if signal.target_estimated_departure_at
        else 0
    )
    predicted_delay_minutes = max(
        0,
        MINIMUM_TURNAROUND_MINUTES - turnaround_minutes,
        official_delay_minutes,
    )
    confidence = _confidence(signal)
    upper_padding = {"high": 15, "medium": 25, "low": 40}[confidence]
    lower_padding = 5 if confidence == "high" else 10

    risk_score = 15 + _turnaround_risk(turnaround_minutes)
    risk_score += 20 if incoming_delay_minutes >= 45 else 10 if incoming_delay_minutes >= 15 else 0
    risk_score += 20 if official_delay_minutes >= 30 else 10 if official_delay_minutes >= 15 else 0
    risk_score += 5 if signal.incoming_status == "active" else 0
    bounded_risk_score = max(5, min(95, risk_score))

    return IncomingDelayEstimate(
        risk=_risk_level(bounded_risk_score),
        risk_score=bounded_risk_score,
        confidence=confidence,
        predicted_delay_min_minutes=max(0, predicted_delay_minutes - lower_padding),
        predicted_delay_max_minutes=max(15, predicted_delay_minutes + upper_padding),
        turnaround_minutes=turnaround_minutes,
        factor_codes=_factor_codes(
            signal=signal,
            incoming_delay_minutes=incoming_delay_minutes,
            official_delay_minutes=official_delay_minutes,
            turnaround_minutes=turnaround_minutes,
        ),
    )


def _confidence(signal: DelayPredictionSignal) -> DelayConfidence:
    if signal.incoming_freshness == "stale":
        return "low"
    if signal.incoming_actual_arrival_at or signal.incoming_estimated_arrival_at:
        return "high"
    return "medium"


def _turnaround_risk(turnaround_minutes: int) -> int:
    if turnaround_minutes < 0:
        return 65
    if turnaround_minutes < 30:
        return 50
    if turnaround_minutes < MINIMUM_TURNAROUND_MINUTES:
        return 35
    if turnaround_minutes < 75:
        return 15
    return 0


def _risk_level(risk_score: int) -> DelayRisk:
    if risk_score >= 75:
        return "high"
    if risk_score >= 45:
        return "elevated"
    return "low"


def _factor_codes(
    *,
    signal: DelayPredictionSignal,
    incoming_delay_minutes: int,
    official_delay_minutes: int,
    turnaround_minutes: int,
) -> tuple[DelayFactorCode, ...]:
    factors: list[DelayFactorCode] = []
    if signal.incoming_status == "landed":
        factors.append("incoming_landed")
    if incoming_delay_minutes >= 15:
        factors.append("incoming_running_late")
    if turnaround_minutes < MINIMUM_TURNAROUND_MINUTES:
        factors.append("tight_turnaround")
    elif turnaround_minutes >= 75:
        factors.append("healthy_turnaround")
    if signal.incoming_status == "active":
        factors.append("incoming_airborne")
    if official_delay_minutes >= 15:
        factors.append("official_delay_signal")
    if signal.incoming_freshness == "stale":
        factors.append("stale_observation")
    return tuple(factors)
