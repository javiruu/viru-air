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
    feet_to_metres,
    knots_to_metres_per_second,
    normalize_identifier,
    remote_failure,
)


class AdsbExchangeOperationalFlightProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        header_name: str = "api-auth",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._header_name = header_name
        self._session = requests.Session()

    def fetch(
        self,
        identity: OperationalFlightIdentity,
        now: dt.datetime,
    ) -> OperationalFetchOutcome:
        search_by, identifier = _identifier(identity)
        if not identifier:
            return OperationalNoCoverage(reason="no_match")
        try:
            response = self._session.get(
                f"{self._base_url}/{search_by}/{identifier}",
                headers={self._header_name: self._api_key},
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
            aircraft = payload.get("ac") if isinstance(payload, dict) else None
        except (ValueError, TypeError):
            return OperationalUnavailable(reason="invalid_payload")
        if not isinstance(aircraft, list):
            return OperationalNoCoverage(reason="no_match")
        matches = [item for item in aircraft if isinstance(item, dict) and _matches(item, identity)]
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


def _identifier(identity: OperationalFlightIdentity) -> tuple[str, str]:
    if identity.icao24:
        return "icao", normalize_identifier(identity.icao24).lower()
    if identity.callsign:
        return "callsign", normalize_identifier(identity.callsign)
    return "icao", ""


def _matches(aircraft: dict[object, object], identity: OperationalFlightIdentity) -> bool:
    if identity.icao24:
        return normalize_identifier(str(aircraft.get("hex", ""))) == normalize_identifier(
            identity.icao24
        )
    return normalize_identifier(str(aircraft.get("flight", ""))) == normalize_identifier(
        identity.callsign
    )


def _to_observation(
    aircraft: dict[object, object],
    now: dt.datetime,
) -> OperationalFlightObservation | None:
    latitude = bounded(aircraft.get("lat"), -90, 90)
    longitude = bounded(aircraft.get("lon"), -180, 180)
    if latitude is None or longitude is None:
        return None
    altitude_raw = aircraft.get("alt_baro")
    on_ground = altitude_raw == "ground"
    return OperationalFlightObservation(
        provider="adsb_exchange",
        provider_flight_id=clean_text(aircraft.get("hex"), 80),
        flight_number=None,
        callsign=clean_text(aircraft.get("flight"), 32),
        icao24=(clean_text(aircraft.get("hex"), 16) or "").lower() or None,
        status="landed" if on_ground else "active",
        status_raw="ground" if on_ground else "airborne",
        observed_at=now,
        expires_at=now + dt.timedelta(seconds=15),
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
        altitude_m=None if on_ground else feet_to_metres(altitude_raw),
        speed_mps=knots_to_metres_per_second(aircraft.get("gs")),
        heading_deg=bounded(aircraft.get("track"), 0, 360),
        on_ground=on_ground,
        registration=clean_text(aircraft.get("r"), 32),
        aircraft_iata=None,
        aircraft_icao=clean_text(aircraft.get("t"), 16),
        data_quality="observed",
    )
