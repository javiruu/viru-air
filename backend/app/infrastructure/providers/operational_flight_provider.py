from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal, Protocol


OperationalStatus = Literal[
    "scheduled",
    "active",
    "landed",
    "cancelled",
    "diverted",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class OperationalFlightIdentity:
    flight_instance_fingerprint: str
    flight_number: str | None
    carrier_code: str | None
    origin_iata: str
    destination_iata: str
    departure_date_local: dt.date | None
    scheduled_departure_at: dt.datetime | None
    scheduled_arrival_at: dt.datetime | None
    callsign: str | None = None
    icao24: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalFlightObservation:
    provider: str
    provider_flight_id: str | None
    flight_number: str | None
    callsign: str | None
    icao24: str | None
    status: OperationalStatus
    status_raw: str | None
    observed_at: dt.datetime
    expires_at: dt.datetime
    scheduled_departure_at: dt.datetime | None
    estimated_departure_at: dt.datetime | None
    actual_departure_at: dt.datetime | None
    scheduled_arrival_at: dt.datetime | None
    estimated_arrival_at: dt.datetime | None
    actual_arrival_at: dt.datetime | None
    departure_terminal: str | None
    departure_gate: str | None
    arrival_terminal: str | None
    arrival_gate: str | None
    departure_delay_minutes: int | None
    arrival_delay_minutes: int | None
    latitude: float | None
    longitude: float | None
    altitude_m: float | None
    speed_mps: float | None
    heading_deg: float | None
    on_ground: bool | None
    registration: str | None
    aircraft_iata: str | None
    aircraft_icao: str | None
    data_quality: str


@dataclass(frozen=True, slots=True)
class OperationalObserved:
    observation: OperationalFlightObservation


@dataclass(frozen=True, slots=True)
class OperationalNoCoverage:
    reason: Literal["no_match", "ambiguous"]


@dataclass(frozen=True, slots=True)
class OperationalRateLimited:
    retry_after_seconds: int


@dataclass(frozen=True, slots=True)
class OperationalUnavailable:
    reason: str


@dataclass(frozen=True, slots=True)
class OperationalNotConfigured:
    provider: str = "none"


OperationalFetchOutcome = (
    OperationalObserved
    | OperationalNoCoverage
    | OperationalRateLimited
    | OperationalUnavailable
    | OperationalNotConfigured
)


class OperationalFlightProvider(Protocol):
    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome: ...
