from __future__ import annotations

import datetime as dt

import requests

from app.infrastructure.providers.operational_flight_provider import (
    OperationalFetchOutcome,
    OperationalFlightIdentity,
    OperationalFlightObservation,
    OperationalNoCoverage,
    OperationalObserved,
    OperationalUnavailable,
)
from app.infrastructure.providers.operational_provider_support import (
    bounded,
    clean_text,
    normalize_identifier,
    parse_timestamp,
    remote_failure,
    safe_observed_at,
)


class OpenSkyOperationalFlightProvider:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._auth = (username, password) if username and password else None
        self._session = requests.Session()

    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        if not identity.icao24 and not identity.callsign:
            return OperationalNoCoverage(reason="no_match")
        params = {"icao24": identity.icao24.lower()} if identity.icao24 else {}
        try:
            response = self._session.get(
                f"{self._base_url}/states/all",
                params=params,
                auth=self._auth,
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
            states = payload.get("states") if isinstance(payload, dict) else None
        except (ValueError, TypeError):
            return OperationalUnavailable(reason="invalid_payload")
        if not isinstance(states, list):
            return OperationalNoCoverage(reason="no_match")
        matches = [state for state in states if _matches(state, identity)]
        if len(matches) > 1:
            return OperationalNoCoverage(reason="ambiguous")
        if not matches:
            return OperationalNoCoverage(reason="no_match")
        observation = _to_observation(matches[0], payload, now)
        return (
            OperationalObserved(observation)
            if observation
            else OperationalUnavailable(reason="invalid_observation")
        )


def _matches(state: object, identity: OperationalFlightIdentity) -> bool:
    if not isinstance(state, list) or len(state) < 17:
        return False
    if identity.icao24 and normalize_identifier(str(state[0])) != normalize_identifier(
        identity.icao24
    ):
        return False
    if identity.callsign and normalize_identifier(str(state[1])) != normalize_identifier(
        identity.callsign
    ):
        return False
    return True


def _to_observation(
    state: list[object],
    payload: dict[object, object],
    now: dt.datetime,
) -> OperationalFlightObservation | None:
    latitude = bounded(state[6], -90, 90)
    longitude = bounded(state[5], -180, 180)
    if latitude is None or longitude is None:
        return None
    observed_at = safe_observed_at(
        parse_timestamp(state[4]) or parse_timestamp(payload.get("time")),
        now,
    )
    if observed_at is None:
        return None
    on_ground = state[8] if isinstance(state[8], bool) else None
    return OperationalFlightObservation(
        provider="opensky",
        provider_flight_id=clean_text(state[0], 80),
        flight_number=None,
        callsign=clean_text(state[1], 32),
        icao24=(clean_text(state[0], 16) or "").lower() or None,
        status="landed" if on_ground else "active",
        status_raw="on_ground" if on_ground else "airborne",
        observed_at=observed_at,
        expires_at=observed_at + dt.timedelta(seconds=15),
        scheduled_departure_at=None,
        estimated_departure_at=None,
        actual_departure_at=None,
        scheduled_arrival_at=None,
        estimated_arrival_at=None,
        actual_arrival_at=None,
        departure_terminal=None,
        departure_gate=None,
        arrival_terminal=None,
        arrival_gate=None,
        departure_delay_minutes=None,
        arrival_delay_minutes=None,
        latitude=latitude,
        longitude=longitude,
        altitude_m=bounded(state[7], -500, 30_000),
        speed_mps=bounded(state[9], 0, 700),
        heading_deg=bounded(state[10], 0, 360),
        on_ground=on_ground,
        registration=None,
        aircraft_iata=None,
        aircraft_icao=None,
        data_quality="observed",
    )
