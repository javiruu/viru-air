from __future__ import annotations

import datetime as dt
from collections.abc import Mapping

import requests

from app.infrastructure.providers.operational_flight_provider import (
    OperationalFetchOutcome,
    OperationalFlightIdentity,
    OperationalFlightObservation,
    OperationalNoCoverage,
    OperationalObserved,
    OperationalStatus,
    OperationalUnavailable,
)
from app.infrastructure.providers.operational_provider_support import (
    bounded,
    clean_text,
    feet_to_metres,
    knots_to_metres_per_second,
    normalize_identifier,
    parse_datetime,
    remote_failure,
    safe_observed_at,
)


class FlightAwareOperationalFlightProvider:
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
        flight_date = identity.departure_date_local or now.date()
        start = (
            dt.datetime.combine(flight_date - dt.timedelta(days=1), dt.time.min).isoformat() + "Z"
        )
        end = dt.datetime.combine(flight_date + dt.timedelta(days=2), dt.time.min).isoformat() + "Z"
        params: dict[str, str | int] = {"start": start, "end": end, "max_pages": 1}
        try:
            response = self._session.get(
                f"{self._base_url}/flights/{normalize_identifier(identity.flight_number)}",
                params=params,
                headers={"x-apikey": self._api_key},
                timeout=self._timeout_seconds,
            )
        except requests.Timeout:
            return OperationalUnavailable(reason="timeout")
        except requests.ConnectionError:
            return OperationalUnavailable(reason="connection")
        except requests.RequestException:
            return OperationalUnavailable(reason="request")
        failure = remote_failure(response.status_code, response.headers)
        if failure is not None:
            return failure
        try:
            payload = response.json()
            flights = payload.get("flights") if isinstance(payload, dict) else None
        except (ValueError, TypeError):
            return OperationalUnavailable(reason="invalid_payload")
        if not isinstance(flights, list):
            return OperationalUnavailable(reason="invalid_payload")
        matches = [item for item in flights if isinstance(item, dict) and _matches(item, identity)]
        if len(matches) > 1:
            matches.sort(key=lambda item: _schedule_distance(item, identity))
            if _schedule_distance(matches[0], identity) == _schedule_distance(matches[1], identity):
                return OperationalNoCoverage(reason="ambiguous")
        if not matches:
            return OperationalNoCoverage(reason="no_match")
        observation = _to_observation(matches[0], now)
        return (
            OperationalObserved(observation)
            if observation
            else OperationalUnavailable(reason="invalid_observation")
        )


def _matches(flight: dict[str, object], identity: OperationalFlightIdentity) -> bool:
    number = flight.get("ident_iata") or flight.get("ident") or flight.get("ident_icao")
    if normalize_identifier(str(number or "")) != normalize_identifier(identity.flight_number):
        return False
    if (
        identity.scheduled_departure_at is not None
        and _schedule_distance(flight, identity) > 43_200
    ):
        return False
    origin = flight.get("origin")
    destination = flight.get("destination")
    return (
        _airport_code(origin) == identity.origin_iata
        and _airport_code(destination) == identity.destination_iata
    )


def _airport_code(value: object) -> str:
    return str(value.get("code_iata") or "").upper() if isinstance(value, dict) else ""


def _schedule_distance(flight: dict[str, object], identity: OperationalFlightIdentity) -> float:
    scheduled = parse_datetime(flight.get("scheduled_out"))
    if scheduled is None or identity.scheduled_departure_at is None:
        return float("inf")
    return abs((scheduled - identity.scheduled_departure_at).total_seconds())


def _to_observation(
    flight: dict[str, object],
    now: dt.datetime,
) -> OperationalFlightObservation | None:
    position = _mapping(flight.get("last_position"))
    raw_status = clean_text(flight.get("status"), 64) or ""
    status = _status(flight, raw_status)
    observed_at = safe_observed_at(parse_datetime(position.get("timestamp")), now)
    if observed_at is None:
        return None
    latitude = bounded(position.get("latitude"), -90, 90)
    longitude = bounded(position.get("longitude"), -180, 180)
    if latitude is None or longitude is None:
        latitude = longitude = None
    return OperationalFlightObservation(
        provider="flightaware",
        provider_flight_id=clean_text(flight.get("fa_flight_id"), 80),
        flight_number=clean_text(flight.get("ident_iata") or flight.get("ident"), 32),
        callsign=clean_text(flight.get("ident_icao"), 32),
        icao24=None,
        status=status,
        status_raw=raw_status or None,
        observed_at=observed_at,
        expires_at=observed_at + dt.timedelta(seconds=60 if status == "active" else 300),
        scheduled_departure_at=parse_datetime(flight.get("scheduled_out")),
        estimated_departure_at=parse_datetime(flight.get("estimated_out")),
        actual_departure_at=parse_datetime(flight.get("actual_out")),
        scheduled_arrival_at=parse_datetime(flight.get("scheduled_in")),
        estimated_arrival_at=parse_datetime(flight.get("estimated_in")),
        actual_arrival_at=parse_datetime(flight.get("actual_in")),
        departure_terminal=_text(flight.get("terminal_origin")),
        departure_gate=_text(flight.get("gate_origin")),
        arrival_terminal=_text(flight.get("terminal_destination")),
        arrival_gate=_text(flight.get("gate_destination")),
        departure_delay_minutes=_seconds_to_minutes(flight.get("departure_delay")),
        arrival_delay_minutes=_seconds_to_minutes(flight.get("arrival_delay")),
        latitude=latitude,
        longitude=longitude,
        altitude_m=feet_to_metres(_hundreds_of_feet(position.get("altitude"))),
        speed_mps=knots_to_metres_per_second(position.get("groundspeed")),
        heading_deg=bounded(position.get("heading"), 0, 360),
        on_ground=status == "landed" if status in {"active", "landed"} else None,
        registration=clean_text(flight.get("registration"), 32),
        aircraft_iata=None,
        aircraft_icao=clean_text(flight.get("aircraft_type"), 16),
        data_quality="observed" if latitude is not None else "status_only",
    )


def _status(flight: dict[str, object], raw_status: str) -> OperationalStatus:
    if flight.get("cancelled") is True:
        return "cancelled"
    if flight.get("diverted") is True:
        return "diverted"
    normalized = raw_status.lower()
    if "en route" in normalized or "airborne" in normalized:
        return "active"
    if "arrived" in normalized or "landed" in normalized:
        return "landed"
    if normalized:
        return "scheduled"
    return "unknown"


def _hundreds_of_feet(value: object) -> float | None:
    return float(value) * 100 if isinstance(value, int | float) else None


def _seconds_to_minutes(value: object) -> int | None:
    return round(float(value) / 60) if isinstance(value, int | float) else None


def _text(value: object) -> str | None:
    return clean_text(value, 32)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}
