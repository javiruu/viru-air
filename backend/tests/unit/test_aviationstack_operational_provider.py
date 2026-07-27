import datetime as dt
from typing import Any

import pytest
import requests

from app.infrastructure.providers.aviationstack_operational_provider import (
    AviationstackOperationalFlightProvider,
    build_operational_provider,
)
from app.infrastructure.providers.operational_flight_provider import (
    OperationalFlightIdentity,
    OperationalNoCoverage,
    OperationalNotConfigured,
    OperationalObserved,
    OperationalRateLimited,
    OperationalUnavailable,
)


class _Response:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _identity(flight_number: str | None = "FR9602") -> OperationalFlightIdentity:
    return OperationalFlightIdentity(
        flight_instance_fingerprint="flight-instance",
        flight_number=flight_number,
        carrier_code="FR",
        origin_iata="MAD",
        destination_iata="FCO",
        departure_date_local=dt.date(2026, 7, 22),
        scheduled_departure_at=dt.datetime(2026, 7, 22, 8, 30),
        scheduled_arrival_at=dt.datetime(2026, 7, 22, 10, 55),
    )


def _flight(
    *,
    status: str = "active",
    departure: str = "2026-07-22T08:30:00+00:00",
    live: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "flight_date": "2026-07-22",
        "flight_status": status,
        "departure": {
            "iata": "MAD",
            "scheduled": departure,
            "estimated": departure,
            "terminal": "1",
            "gate": "B12",
            "delay": 5,
        },
        "arrival": {
            "iata": "FCO",
            "scheduled": "2026-07-22T10:55:00+00:00",
            "terminal": "3",
            "gate": "E8",
        },
        "airline": {"iata": "FR"},
        "flight": {"number": "9602", "iata": "FR9602", "icao": "RYR9602"},
        "aircraft": {"registration": "EI-TEST", "icao24": "4ca123"},
        "live": live,
    }


def _provider() -> AviationstackOperationalFlightProvider:
    return AviationstackOperationalFlightProvider("secret", "https://provider.test/v1", 4.0)


def test_provider_configuration_is_optional_and_invalid_timeout_falls_back(monkeypatch) -> None:
    monkeypatch.delenv("AVIATIONSTACK_API_KEY", raising=False)
    assert isinstance(build_operational_provider(), OperationalNotConfigured)

    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "secret")
    monkeypatch.setenv("AVIATIONSTACK_TIMEOUT_SECONDS", "not-a-number")
    provider = build_operational_provider()

    assert isinstance(provider, AviationstackOperationalFlightProvider)
    assert provider._timeout_seconds == 8.0


def test_provider_selects_closest_exact_route_and_sanitizes_live_telemetry(
    monkeypatch,
    caplog,
) -> None:
    provider = _provider()
    requested: dict[str, Any] = {}

    def fake_get(url: str, *, params: dict[str, Any], timeout: float) -> _Response:
        requested.update(url=url, params=params, timeout=timeout)
        return _Response(
            200,
            {
                "data": [
                    _flight(departure="2026-07-22T12:30:00+00:00"),
                    _flight(
                        live={
                            "updated": "2026-07-22T08:45:00+00:00",
                            "latitude": 41.1,
                            "longitude": 2.1,
                            "altitude": 99999,
                            "direction": 500,
                            "speed_horizontal": -5,
                            "is_ground": False,
                        }
                    ),
                ]
            },
        )

    monkeypatch.setattr(provider._session, "get", fake_get)
    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 46))

    assert isinstance(outcome, OperationalObserved)
    observation = outcome.observation
    assert observation.status == "active"
    assert observation.latitude == 41.1
    assert observation.longitude == 2.1
    assert observation.altitude_m is None
    assert observation.heading_deg is None
    assert observation.speed_mps is None
    assert observation.expires_at - observation.observed_at == dt.timedelta(seconds=60)
    assert requested["params"]["flight_iata"] == "FR9602"
    assert "flight_date" not in requested["params"]
    assert requested["timeout"] == 4.0
    assert "secret" not in caplog.text


def test_provider_rejects_ambiguous_matches_and_incomplete_position(monkeypatch) -> None:
    provider = _provider()
    candidate = _flight(live={"latitude": 41.1, "longitude": None})
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(200, {"data": [candidate, candidate]}),
    )

    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 30))

    assert isinstance(outcome, OperationalNoCoverage)
    assert outcome.reason == "ambiguous"


def test_provider_uses_free_lookup_and_converts_speed(monkeypatch) -> None:
    provider = _provider()
    requested: dict[str, Any] = {}

    def fake_get(url: str, *, params: dict[str, Any], timeout: float) -> _Response:
        requested.update(params)
        return _Response(
            200,
            {
                "data": [
                    _flight(
                        live={
                            "updated": "2026-07-21T15:31:00+00:00",
                            "latitude": 41.1,
                            "longitude": 2.1,
                            "speed_horizontal": 764.424,
                        }
                    )
                ]
            },
        )

    identity = OperationalFlightIdentity(
        flight_instance_fingerprint="flight-local-date",
        flight_number="FR9602",
        carrier_code="FR",
        origin_iata="MAD",
        destination_iata="FCO",
        departure_date_local=dt.date(2026, 7, 22),
        scheduled_departure_at=None,
        scheduled_arrival_at=None,
    )
    monkeypatch.setattr(provider._session, "get", fake_get)

    outcome = provider.fetch(identity, dt.datetime(2026, 7, 21, 15, 32))

    assert "flight_date" not in requested
    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.speed_mps == pytest.approx(212.34)


def test_provider_rejects_schedule_far_from_saved_flight(monkeypatch) -> None:
    provider = _provider()
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(
            200,
            {"data": [_flight(departure="2026-07-23T08:30:00+00:00")]},
        ),
    )

    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 30))

    assert isinstance(outcome, OperationalNoCoverage)
    assert outcome.reason == "no_match"


def test_provider_rejects_wrong_local_date_without_saved_utc_schedule(monkeypatch) -> None:
    provider = _provider()
    identity = OperationalFlightIdentity(
        flight_instance_fingerprint="flight-local-date-only",
        flight_number="FR9602",
        carrier_code="FR",
        origin_iata="MAD",
        destination_iata="FCO",
        departure_date_local=dt.date(2026, 7, 22),
        scheduled_departure_at=None,
        scheduled_arrival_at=None,
    )
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(
            200,
            {"data": [_flight(departure="2026-07-23T08:30:00+00:00")]},
        ),
    )

    outcome = provider.fetch(identity, dt.datetime(2026, 7, 22, 8, 30))

    assert isinstance(outcome, OperationalNoCoverage)
    assert outcome.reason == "no_match"


def test_provider_rejects_observation_with_impossible_future_timestamp(monkeypatch) -> None:
    provider = _provider()
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(
            200,
            {
                "data": [
                    _flight(
                        live={
                            "updated": "2026-07-22T10:00:00+00:00",
                            "latitude": 41.1,
                            "longitude": 2.1,
                        }
                    )
                ]
            },
        ),
    )

    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 30))

    assert isinstance(outcome, OperationalUnavailable)
    assert outcome.reason == "invalid_observation"


@pytest.mark.parametrize(
    ("response", "outcome_type"),
    [
        (_Response(429, {}), OperationalRateLimited),
        (_Response(401, {}), OperationalUnavailable),
        (_Response(503, {}), OperationalUnavailable),
        (_Response(200, ValueError("invalid json")), OperationalUnavailable),
        (_Response(200, {"unexpected": []}), OperationalUnavailable),
    ],
)
def test_provider_maps_remote_failures_without_raising(monkeypatch, response, outcome_type) -> None:
    provider = _provider()
    monkeypatch.setattr(provider._session, "get", lambda *args, **kwargs: response)

    assert isinstance(
        provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 30)),
        outcome_type,
    )


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (requests.Timeout(), "timeout"),
        (requests.ConnectionError(), "connection"),
        (requests.RequestException(), "request"),
    ],
)
def test_provider_maps_network_failures_without_raising(monkeypatch, error, reason: str) -> None:
    provider = _provider()

    def fake_get(*args, **kwargs):
        raise error

    monkeypatch.setattr(provider._session, "get", fake_get)
    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 30))

    assert isinstance(outcome, OperationalUnavailable)
    assert outcome.reason == reason


def test_provider_does_not_call_remote_api_without_flight_number(monkeypatch) -> None:
    provider = _provider()

    def unexpected_call(*args, **kwargs):
        raise AssertionError("remote provider must not be called")

    monkeypatch.setattr(provider._session, "get", unexpected_call)
    outcome = provider.fetch(_identity(None), dt.datetime(2026, 7, 22, 8, 30))

    assert isinstance(outcome, OperationalNoCoverage)
    assert outcome.reason == "no_match"
