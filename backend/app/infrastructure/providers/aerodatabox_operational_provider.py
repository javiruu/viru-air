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
    delay_minutes,
    normalize_identifier,
    parse_datetime,
    remote_failure,
    safe_observed_at,
)


class AeroDataBoxOperationalFlightProvider:
    def __init__(
        self, api_key: str, base_url: str, host_header: str, timeout_seconds: float
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._host_header = host_header
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        if not identity.flight_number:
            return OperationalNoCoverage(reason="no_match")
        departure_date = identity.departure_date_local or (
            identity.scheduled_departure_at.date()
            if identity.scheduled_departure_at
            else now.date()
        )
        flight_number = normalize_identifier(identity.flight_number)
        try:
            response = self._session.get(
                f"{self._base_url}/flights/number/{flight_number}/{departure_date.isoformat()}",
                params={
                    "dateLocalRole": "Departure",
                    "withAircraftImage": "false",
                    "withLocation": "true",
                    "withFlightPlan": "false",
                },
                headers={
                    "X-RapidAPI-Key": self._api_key,
                    "X-RapidAPI-Host": self._host_header,
                },
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
        if response.status_code == 204:
            return OperationalNoCoverage(reason="no_match")
        try:
            payload = response.json()
        except (ValueError, TypeError):
            return OperationalUnavailable(reason="invalid_payload")
        if not isinstance(payload, list):
            return OperationalUnavailable(reason="invalid_payload")
        matches = [item for item in payload if isinstance(item, dict) and _matches(item, identity)]
        if len(matches) > 1:
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
    if normalize_identifier(str(flight.get("number") or "")) != normalize_identifier(
        identity.flight_number
    ):
        return False
    departure = flight.get("departure")
    arrival = flight.get("arrival")
    if not isinstance(departure, dict) or not isinstance(arrival, dict):
        return False
    return (
        _airport_iata(departure) == identity.origin_iata
        and _airport_iata(arrival) == identity.destination_iata
    )


def _airport_iata(movement: dict[object, object]) -> str:
    airport = movement.get("airport")
    return str(airport.get("iata") or "").upper() if isinstance(airport, dict) else ""


def _utc_time(movement: dict[object, object], field: str) -> dt.datetime | None:
    value = movement.get(field)
    return parse_datetime(value.get("utc")) if isinstance(value, dict) else None


def _to_observation(
    flight: dict[str, object],
    now: dt.datetime,
) -> OperationalFlightObservation | None:
    departure = flight.get("departure")
    arrival = flight.get("arrival")
    if not isinstance(departure, dict) or not isinstance(arrival, dict):
        return None
    raw_status = clean_text(flight.get("status"), 64) or ""
    status = _status(raw_status)
    scheduled_departure = _utc_time(departure, "scheduledTime")
    revised_departure = _utc_time(departure, "revisedTime")
    scheduled_arrival = _utc_time(arrival, "scheduledTime")
    revised_arrival = _utc_time(arrival, "revisedTime")
    location = _mapping(flight.get("location"))
    aircraft = _mapping(flight.get("aircraft"))
    observed_at = safe_observed_at(
        parse_datetime(location.get("reportedAtUtc"))
        or parse_datetime(flight.get("lastUpdatedUtc")),
        now,
    )
    if observed_at is None:
        return None
    latitude = bounded(location.get("lat"), -90, 90)
    longitude = bounded(location.get("lon"), -180, 180)
    if latitude is None or longitude is None:
        latitude = longitude = None
    altitude = location.get("altitude")
    speed = location.get("groundSpeed")
    track = location.get("trueTrack")
    completed = status in {"landed", "cancelled", "diverted"}
    return OperationalFlightObservation(
        provider="aerodatabox",
        provider_flight_id=normalize_identifier(str(flight.get("number") or "")),
        flight_number=clean_text(flight.get("number"), 32),
        callsign=clean_text(flight.get("callSign"), 32),
        icao24=(clean_text(aircraft.get("modeS"), 16) or "").lower() or None,
        status=status,
        status_raw=raw_status or None,
        observed_at=observed_at,
        expires_at=observed_at + dt.timedelta(seconds=60 if status == "active" else 300),
        scheduled_departure_at=scheduled_departure,
        estimated_departure_at=None if status == "active" or completed else revised_departure,
        actual_departure_at=revised_departure if status == "active" or completed else None,
        scheduled_arrival_at=scheduled_arrival,
        estimated_arrival_at=None if completed else revised_arrival,
        actual_arrival_at=revised_arrival if status == "landed" else None,
        departure_terminal=_text(departure.get("terminal")),
        departure_gate=_text(departure.get("gate")),
        arrival_terminal=_text(arrival.get("terminal")),
        arrival_gate=_text(arrival.get("gate")),
        departure_delay_minutes=delay_minutes(scheduled_departure, revised_departure),
        arrival_delay_minutes=delay_minutes(scheduled_arrival, revised_arrival),
        latitude=latitude,
        longitude=longitude,
        altitude_m=bounded(altitude.get("meter"), -500, 30_000)
        if isinstance(altitude, dict)
        else None,
        speed_mps=bounded(speed.get("meterPerSecond"), 0, 700) if isinstance(speed, dict) else None,
        heading_deg=bounded(track.get("deg"), 0, 360) if isinstance(track, dict) else None,
        on_ground=status == "landed" if status in {"active", "landed"} else None,
        registration=clean_text(aircraft.get("reg"), 32),
        aircraft_iata=None,
        aircraft_icao=clean_text(aircraft.get("model"), 16),
        data_quality="observed" if latitude is not None else "status_only",
    )


def _status(value: str) -> OperationalStatus:
    normalized = normalize_identifier(value)
    if normalized in {"ENROUTE", "DEPARTED", "APPROACH", "AIRBORNE"}:
        return "active"
    if normalized in {"ARRIVED", "LANDED"}:
        return "landed"
    if normalized in {"CANCELLED", "CANCELED"}:
        return "cancelled"
    if normalized == "DIVERTED":
        return "diverted"
    if normalized in {"EXPECTED", "CHECKIN", "BOARDING", "GATECLOSED", "DELAYED"}:
        return "scheduled"
    return "unknown"


def _text(value: object) -> str | None:
    return clean_text(value, 32)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}
