from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

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
    clean_text,
    delay_minutes,
    normalize_identifier,
    parse_datetime,
    remote_failure,
)


class AmadeusOperationalFlightProvider:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()
        self._access_token: str | None = None
        self._token_expires_at = dt.datetime.min

    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        if not identity.carrier_code or not identity.flight_number:
            return OperationalNoCoverage(reason="no_match")
        token_outcome = self._token(now)
        if not isinstance(token_outcome, str):
            return token_outcome
        flight_date = identity.departure_date_local or (
            identity.scheduled_departure_at.date()
            if identity.scheduled_departure_at
            else now.date()
        )
        flight_number = _numeric_flight_number(identity.flight_number, identity.carrier_code)
        if not flight_number:
            return OperationalNoCoverage(reason="no_match")
        try:
            response = self._session.get(
                f"{self._base_url}/v2/schedule/flights",
                params={
                    "carrierCode": identity.carrier_code.upper(),
                    "flightNumber": flight_number,
                    "scheduledDepartureDate": flight_date.isoformat(),
                },
                headers={"Authorization": f"Bearer {token_outcome}"},
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
            flights = payload.get("data") if isinstance(payload, dict) else None
        except (ValueError, TypeError):
            return OperationalUnavailable(reason="invalid_payload")
        if not isinstance(flights, list):
            return OperationalUnavailable(reason="invalid_payload")
        matches = [item for item in flights if isinstance(item, dict) and _matches(item, identity)]
        if len(matches) > 1:
            return OperationalNoCoverage(reason="ambiguous")
        if not matches:
            return OperationalNoCoverage(reason="no_match")
        observation = _to_observation(matches[0], identity, now)
        return (
            OperationalObserved(observation)
            if observation
            else OperationalUnavailable(reason="invalid_observation")
        )

    def _token(self, now: dt.datetime) -> str | OperationalFetchOutcome:
        if self._access_token and self._token_expires_at > now:
            return self._access_token
        try:
            response = self._session.post(
                f"{self._base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
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
            token = payload.get("access_token") if isinstance(payload, dict) else None
            expires_in = payload.get("expires_in", 1800) if isinstance(payload, dict) else 1800
        except (ValueError, TypeError):
            return OperationalUnavailable(reason="invalid_payload")
        if not isinstance(token, str) or not token:
            return OperationalUnavailable(reason="invalid_payload")
        lifetime = int(expires_in) if isinstance(expires_in, int | float) else 1800
        self._access_token = token
        self._token_expires_at = now + dt.timedelta(seconds=max(60, lifetime - 60))
        return token


def _matches(flight: dict[str, object], identity: OperationalFlightIdentity) -> bool:
    designator = flight.get("flightDesignator")
    if not isinstance(designator, dict):
        return False
    candidate = f"{designator.get('carrierCode') or ''}{designator.get('flightNumber') or ''}"
    if normalize_identifier(candidate) != normalize_identifier(identity.flight_number):
        return False
    departure, arrival = _points(flight)
    return _iata(departure) == identity.origin_iata and _iata(arrival) == identity.destination_iata


def _points(flight: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    points = flight.get("flightPoints")
    if not isinstance(points, list):
        return {}, {}
    valid = [point for point in points if isinstance(point, dict)]
    return (valid[0], valid[-1]) if len(valid) >= 2 else ({}, {})


def _iata(point: dict[str, object]) -> str:
    return str(point.get("iataCode") or "").upper()


def _movement(point: dict[str, object], name: str) -> dict[str, object]:
    value = point.get(name)
    return value if isinstance(value, dict) else {}


def _timing(movement: dict[str, object], qualifiers: Iterable[str]) -> dt.datetime | None:
    timings = movement.get("timings")
    if not isinstance(timings, list):
        return None
    wanted = set(qualifiers)
    for timing in timings:
        if isinstance(timing, dict) and timing.get("qualifier") in wanted:
            parsed = parse_datetime(timing.get("value"))
            if parsed is not None:
                return parsed
    return None


def _code(movement: dict[str, object], field: str, nested_field: str) -> str | None:
    value = movement.get(field)
    if isinstance(value, dict):
        result = value.get(nested_field) or value.get("code")
        return clean_text(result, 32)
    return clean_text(value, 32)


def _to_observation(
    flight: dict[str, object],
    identity: OperationalFlightIdentity,
    now: dt.datetime,
) -> OperationalFlightObservation | None:
    departure_point, arrival_point = _points(flight)
    departure = _movement(departure_point, "departure")
    arrival = _movement(arrival_point, "arrival")
    if not departure or not arrival:
        return None
    scheduled_departure = _timing(departure, ("STD",))
    estimated_departure = _timing(departure, ("ETD",))
    actual_departure = _timing(departure, ("ATD",))
    scheduled_arrival = _timing(arrival, ("STA",))
    estimated_arrival = _timing(arrival, ("ETA",))
    actual_arrival = _timing(arrival, ("ATA",))
    raw_status = clean_text(flight.get("flightStatus"), 64) or ""
    status = _status(raw_status, actual_departure, actual_arrival)
    return OperationalFlightObservation(
        provider="amadeus",
        provider_flight_id=normalize_identifier(identity.flight_number),
        flight_number=identity.flight_number,
        callsign=None,
        icao24=None,
        status=status,
        status_raw=raw_status or None,
        observed_at=now,
        expires_at=now + dt.timedelta(seconds=60 if status == "active" else 300),
        scheduled_departure_at=scheduled_departure,
        estimated_departure_at=estimated_departure,
        actual_departure_at=actual_departure,
        scheduled_arrival_at=scheduled_arrival,
        estimated_arrival_at=estimated_arrival,
        actual_arrival_at=actual_arrival,
        departure_terminal=_code(departure, "terminal", "code"),
        departure_gate=_code(departure, "gate", "mainGate"),
        arrival_terminal=_code(arrival, "terminal", "code"),
        arrival_gate=_code(arrival, "gate", "mainGate"),
        departure_delay_minutes=delay_minutes(
            scheduled_departure, actual_departure or estimated_departure
        ),
        arrival_delay_minutes=delay_minutes(scheduled_arrival, actual_arrival or estimated_arrival),
        latitude=None,
        longitude=None,
        altitude_m=None,
        speed_mps=None,
        heading_deg=None,
        on_ground=status == "landed" if status in {"active", "landed"} else None,
        registration=None,
        aircraft_iata=None,
        aircraft_icao=None,
        data_quality="status_only",
    )


def _status(
    raw_status: str,
    actual_departure: dt.datetime | None,
    actual_arrival: dt.datetime | None,
) -> OperationalStatus:
    normalized = normalize_identifier(raw_status)
    if normalized in {"CANCELLED", "CANCELED"}:
        return "cancelled"
    if normalized == "DIVERTED":
        return "diverted"
    if actual_arrival is not None or normalized in {"ARRIVED", "LANDED"}:
        return "landed"
    if actual_departure is not None or normalized in {"DEPARTED", "ENROUTE", "AIRBORNE"}:
        return "active"
    return "scheduled" if raw_status or normalized == "" else "unknown"


def _numeric_flight_number(flight_number: str, carrier_code: str) -> str:
    normalized = normalize_identifier(flight_number)
    carrier = normalize_identifier(carrier_code)
    return normalized.removeprefix(carrier)
