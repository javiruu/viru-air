from __future__ import annotations

import datetime as dt
import logging
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.infrastructure.providers.operational_flight_provider import (
    OperationalFetchOutcome,
    OperationalFlightIdentity,
    OperationalFlightObservation,
    OperationalStatus,
    OperationalNoCoverage,
    OperationalNotConfigured,
    OperationalObserved,
    OperationalRateLimited,
    OperationalUnavailable,
)


logger = logging.getLogger("app.live_flight.aviationstack")
MAX_SCHEDULE_DELTA_SECONDS = 12 * 60 * 60
MAX_PROVIDER_CLOCK_SKEW = dt.timedelta(minutes=5)


class _AirportData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    iata: str | None = Field(default=None, max_length=3)
    scheduled: dt.datetime | None = None
    estimated: dt.datetime | None = None
    actual: dt.datetime | None = None
    terminal: str | None = Field(default=None, max_length=32)
    gate: str | None = Field(default=None, max_length=32)
    delay: int | None = None


class _AirlineData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    iata: str | None = Field(default=None, max_length=3)


class _FlightData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    number: str | None = Field(default=None, max_length=32)
    iata: str | None = Field(default=None, max_length=32)
    icao: str | None = Field(default=None, max_length=32)


class _AircraftData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    registration: str | None = Field(default=None, max_length=32)
    iata: str | None = Field(default=None, max_length=16)
    icao: str | None = Field(default=None, max_length=16)
    icao24: str | None = Field(default=None, max_length=16)


class _LiveData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    updated: dt.datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    direction: float | None = None
    speed_horizontal: float | None = None
    is_ground: bool | None = None


class _AviationstackFlight(BaseModel):
    model_config = ConfigDict(extra="ignore")

    flight_date: dt.date | None = None
    flight_status: str | None = Field(default=None, max_length=64)
    departure: _AirportData
    arrival: _AirportData
    airline: _AirlineData = Field(default_factory=_AirlineData)
    flight: _FlightData
    aircraft: _AircraftData | None = None
    live: _LiveData | None = None


class _AviationstackResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: list[_AviationstackFlight]


class AviationstackOperationalFlightProvider:
    def __init__(self, api_key: str, base_url: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        if not identity.flight_number:
            return OperationalNoCoverage(reason="no_match")
        params: dict[str, str | int] = {
            "access_key": self._api_key,
            "flight_iata": _normalize_flight_number(identity.flight_number),
            "limit": 20,
        }
        try:
            response = self._session.get(
                f"{self._base_url}/flights",
                params=params,
                timeout=self._timeout_seconds,
            )
        except requests.Timeout:
            return OperationalUnavailable(reason="timeout")
        except requests.ConnectionError:
            return OperationalUnavailable(reason="connection")
        except requests.RequestException:
            return OperationalUnavailable(reason="request")

        if response.status_code == 429:
            return OperationalRateLimited(retry_after_seconds=300)
        if response.status_code in {401, 403}:
            return OperationalUnavailable(reason="authentication")
        if response.status_code >= 500:
            return OperationalUnavailable(reason="provider")
        if response.status_code >= 400:
            return OperationalUnavailable(reason="request_rejected")
        try:
            payload = _AviationstackResponse.model_validate(response.json())
        except (ValidationError, ValueError, TypeError):
            return OperationalUnavailable(reason="invalid_payload")

        matched = _select_match(payload.data, identity)
        if matched is None:
            return OperationalNoCoverage(reason="no_match")
        if isinstance(matched, _AmbiguousMatch):
            return OperationalNoCoverage(reason="ambiguous")
        observation = _to_observation(matched, now)
        if observation is None:
            return OperationalUnavailable(reason="invalid_observation")
        logger.info(
            "live_flight_provider_observed provider=aviationstack status=%s",
            observation.status,
        )
        return OperationalObserved(observation=observation)


def build_operational_provider() -> AviationstackOperationalFlightProvider | OperationalNotConfigured:
    api_key = os.getenv("AVIATIONSTACK_API_KEY", "").strip()
    if not api_key:
        return OperationalNotConfigured()
    base_url = os.getenv("AVIATIONSTACK_BASE_URL", "https://api.aviationstack.com/v1").strip()
    timeout_seconds = _timeout_seconds_from_env(os.getenv("AVIATIONSTACK_TIMEOUT_SECONDS"))
    return AviationstackOperationalFlightProvider(api_key, base_url, timeout_seconds)


@dataclass(frozen=True, slots=True)
class _AmbiguousMatch:
    pass


_AMBIGUOUS_MATCH = _AmbiguousMatch()


def _select_match(
    candidates: Sequence[_AviationstackFlight],
    identity: OperationalFlightIdentity,
) -> _AviationstackFlight | _AmbiguousMatch | None:
    expected_number = _normalize_flight_number(identity.flight_number)
    scored: list[tuple[float, _AviationstackFlight]] = []
    for candidate in candidates:
        candidate_number = _normalize_flight_number(
            candidate.flight.iata
            or f"{candidate.airline.iata or ''}{candidate.flight.number or ''}"
        )
        if candidate_number != expected_number:
            continue
        if _normalize_iata(candidate.departure.iata) != identity.origin_iata:
            continue
        if _normalize_iata(candidate.arrival.iata) != identity.destination_iata:
            continue
        expected_date = identity.departure_date_local
        if expected_date is not None and (
            candidate.departure.scheduled is None
            or candidate.departure.scheduled.date() != expected_date
        ):
            continue
        distance = _schedule_distance_seconds(candidate.departure.scheduled, identity.scheduled_departure_at)
        if identity.scheduled_departure_at is not None and distance > MAX_SCHEDULE_DELTA_SECONDS:
            continue
        scored.append((distance, candidate))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return _AMBIGUOUS_MATCH
    return scored[0][1]


def _to_observation(
    flight: _AviationstackFlight,
    now: dt.datetime,
) -> OperationalFlightObservation | None:
    status = _normalize_status(flight.flight_status)
    observed_at = _utc_naive(flight.live.updated if flight.live else None) or now
    if observed_at > now + MAX_PROVIDER_CLOCK_SKEW:
        return None
    ttl_seconds = 60 if status == "active" else 21600 if status in {"landed", "cancelled", "diverted"} else 300
    live = flight.live
    aircraft = flight.aircraft
    latitude = live.latitude if live and live.latitude is not None and -90 <= live.latitude <= 90 else None
    longitude = live.longitude if live and live.longitude is not None and -180 <= live.longitude <= 180 else None
    if latitude is None or longitude is None:
        latitude = None
        longitude = None
    altitude_m = _bounded(live.altitude if live else None, -500, 30000)
    speed_mps = _kilometres_per_hour_to_metres_per_second(
        live.speed_horizontal if live else None
    )
    heading_deg = _bounded(live.direction if live else None, 0, 360)
    return OperationalFlightObservation(
        provider="aviationstack",
        provider_flight_id=flight.flight.iata or flight.flight.icao,
        flight_number=flight.flight.iata,
        callsign=flight.flight.icao,
        icao24=aircraft.icao24 if aircraft else None,
        status=status,
        status_raw=flight.flight_status,
        observed_at=observed_at,
        expires_at=observed_at + dt.timedelta(seconds=ttl_seconds),
        scheduled_departure_at=_utc_naive(flight.departure.scheduled),
        estimated_departure_at=_utc_naive(flight.departure.estimated),
        actual_departure_at=_utc_naive(flight.departure.actual),
        scheduled_arrival_at=_utc_naive(flight.arrival.scheduled),
        estimated_arrival_at=_utc_naive(flight.arrival.estimated),
        actual_arrival_at=_utc_naive(flight.arrival.actual),
        departure_terminal=flight.departure.terminal,
        departure_gate=flight.departure.gate,
        arrival_terminal=flight.arrival.terminal,
        arrival_gate=flight.arrival.gate,
        departure_delay_minutes=flight.departure.delay,
        arrival_delay_minutes=flight.arrival.delay,
        latitude=latitude,
        longitude=longitude,
        altitude_m=altitude_m,
        speed_mps=speed_mps,
        heading_deg=heading_deg,
        on_ground=live.is_ground if live else None,
        registration=aircraft.registration if aircraft else None,
        aircraft_iata=aircraft.iata if aircraft else None,
        aircraft_icao=aircraft.icao if aircraft else None,
        data_quality="observed" if live and latitude is not None else "status_only",
    )


def _normalize_status(value: str | None) -> OperationalStatus:
    normalized = (value or "").strip().lower()
    mapping: dict[str, OperationalStatus] = {
        "scheduled": "scheduled",
        "active": "active",
        "landed": "landed",
        "cancelled": "cancelled",
        "diverted": "diverted",
        "incident": "unknown",
    }
    return mapping.get(normalized, "unknown")


def _bounded(value: float | None, minimum: float, maximum: float) -> float | None:
    if value is None or not minimum <= value <= maximum:
        return None
    return value


def _kilometres_per_hour_to_metres_per_second(value: float | None) -> float | None:
    bounded = _bounded(value, 0, 1800)
    return bounded / 3.6 if bounded is not None else None


def _timeout_seconds_from_env(value: str | None) -> float:
    try:
        parsed = float(value or "8")
    except ValueError:
        return 8.0
    return max(1.0, min(20.0, parsed))


def _normalize_flight_number(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def _normalize_iata(value: str | None) -> str:
    return (value or "").strip().upper()


def _schedule_distance_seconds(candidate: dt.datetime | None, expected: dt.datetime | None) -> float:
    if candidate is None or expected is None:
        return float("inf")
    candidate_value = _utc_naive(candidate)
    expected_value = _utc_naive(expected)
    if candidate_value is None or expected_value is None:
        return float("inf")
    return abs((candidate_value - expected_value).total_seconds())


def _utc_naive(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(dt.UTC).replace(tzinfo=None)
