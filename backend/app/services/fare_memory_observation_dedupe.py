from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Final

from app.infrastructure.db.models import FlightPriceObservation


RECENT_OBSERVATION_DEDUPE_WINDOW: Final = dt.timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class ObservationCandidate:
    provider: str
    price_amount: float
    currency: str
    observed_at: dt.datetime


def is_recent_duplicate_observation(
    previous_observation: FlightPriceObservation | None,
    candidate: ObservationCandidate,
) -> bool:
    if previous_observation is None or previous_observation.price_amount is None:
        return False
    if str(previous_observation.provider).strip().lower() != candidate.provider:
        return False
    if str(previous_observation.currency).strip().upper() != candidate.currency:
        return False
    if abs(float(previous_observation.price_amount) - candidate.price_amount) > 0.0001:
        return False
    return abs(candidate.observed_at - previous_observation.observed_at) <= RECENT_OBSERVATION_DEDUPE_WINDOW
