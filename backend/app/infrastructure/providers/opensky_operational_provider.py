from __future__ import annotations

import datetime as dt
import time

import requests

from app.infrastructure.providers.operational_flight_provider import (
    OperationalFetchOutcome,
    OperationalFlightIdentity,
    OperationalFlightObservation,
    OperationalNoCoverage,
    OperationalObserved,
    OperationalRateLimited,
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
        client_id: str | None = None,
        client_secret: str | None = None,
        token_url: str = (
            "https://auth.opensky-network.org/auth/realms/"
            "opensky-network/protocol/openid-connect/token"
        ),
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._session = requests.Session()

    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        if not identity.icao24 and not identity.callsign:
            return OperationalNoCoverage(reason="no_match")
        params = {"icao24": identity.icao24.lower()} if identity.icao24 else {}
        headers = self._authorization_headers()
        if not isinstance(headers, dict):
            return headers
        try:
            response = self._session.get(
                f"{self._base_url}/states/all",
                params=params,
                headers=headers,
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

    def _authorization_headers(
        self,
    ) -> dict[str, str] | OperationalRateLimited | OperationalUnavailable:
        if not self._client_id or not self._client_secret:
            return {}
        if self._access_token and time.monotonic() < self._token_expires_at:
            return {"Authorization": f"Bearer {self._access_token}"}
        try:
            response = self._session.post(
                self._token_url,
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
            access_token = payload.get("access_token") if isinstance(payload, dict) else None
            expires_in = payload.get("expires_in", 1800) if isinstance(payload, dict) else 1800
            expires_in_seconds = max(60, int(expires_in))
        except (TypeError, ValueError):
            return OperationalUnavailable(reason="invalid_payload")
        if not isinstance(access_token, str) or not access_token:
            return OperationalUnavailable(reason="invalid_payload")
        self._access_token = access_token
        self._token_expires_at = time.monotonic() + max(30, expires_in_seconds - 30)
        return {"Authorization": f"Bearer {access_token}"}


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
