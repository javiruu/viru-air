import datetime as dt
from typing import Any

import pytest

from app.infrastructure.providers.adsb_exchange_operational_provider import (
    AdsbExchangeOperationalFlightProvider,
)
from app.infrastructure.providers.aerodatabox_operational_provider import (
    AeroDataBoxOperationalFlightProvider,
)
from app.infrastructure.providers.amadeus_operational_provider import (
    AmadeusOperationalFlightProvider,
)
from app.infrastructure.providers.flightaware_operational_provider import (
    FlightAwareOperationalFlightProvider,
)
from app.infrastructure.providers.opensky_operational_provider import (
    OpenSkyOperationalFlightProvider,
)
from app.infrastructure.providers.operational_flight_provider import (
    OperationalFlightIdentity,
    OperationalNoCoverage,
    OperationalObserved,
    OperationalRateLimited,
    OperationalUnavailable,
)


class _Response:
    def __init__(
        self, status_code: int, payload: Any, headers: dict[str, str] | None = None
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload


def _identity(**overrides) -> OperationalFlightIdentity:
    values = {
        "flight_instance_fingerprint": "flight-instance",
        "flight_number": "FR9602",
        "carrier_code": "FR",
        "origin_iata": "MAD",
        "destination_iata": "FCO",
        "departure_date_local": dt.date(2026, 7, 22),
        "scheduled_departure_at": dt.datetime(2026, 7, 22, 8, 30),
        "scheduled_arrival_at": dt.datetime(2026, 7, 22, 10, 55),
        "callsign": None,
        "icao24": None,
    }
    values.update(overrides)
    return OperationalFlightIdentity(**values)


def test_amadeus_maps_schedule_status_terminal_and_gate(monkeypatch) -> None:
    provider = AmadeusOperationalFlightProvider("client", "secret", "https://test.api", 4)
    calls = []

    def fake_post(*args, **kwargs):
        return _Response(200, {"access_token": "token", "expires_in": 1800})

    def fake_get(url, *, params, headers, timeout):
        calls.append((url, params, headers, timeout))
        return _Response(
            200,
            {
                "data": [
                    {
                        "type": "DatedFlight",
                        "scheduledDepartureDate": "2026-07-22",
                        "flightDesignator": {"carrierCode": "FR", "flightNumber": 9602},
                        "flightPoints": [
                            {
                                "iataCode": "MAD",
                                "departure": {
                                    "timings": [
                                        {"qualifier": "STD", "value": "2026-07-22T08:30:00Z"},
                                        {"qualifier": "ETD", "value": "2026-07-22T08:40:00Z"},
                                    ],
                                    "terminal": {"code": "1"},
                                    "gate": {"mainGate": "B12"},
                                },
                            },
                            {
                                "iataCode": "FCO",
                                "arrival": {
                                    "timings": [
                                        {"qualifier": "STA", "value": "2026-07-22T10:55:00Z"}
                                    ],
                                    "terminal": {"code": "3"},
                                    "gate": {"mainGate": "E8"},
                                },
                            },
                        ],
                        "flightStatus": "DELAYED",
                    }
                ]
            },
        )

    monkeypatch.setattr(provider._session, "post", fake_post)
    monkeypatch.setattr(provider._session, "get", fake_get)

    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 45))

    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.status == "scheduled"
    assert outcome.observation.departure_gate == "B12"
    assert outcome.observation.departure_delay_minutes == 10
    assert calls[0][2] == {"Authorization": "Bearer token"}


def test_opensky_maps_state_vector_and_retry_after(monkeypatch) -> None:
    provider = OpenSkyOperationalFlightProvider("https://opensky.test/api", 4)
    observed_timestamp = int(dt.datetime(2026, 7, 22, 8, 45, tzinfo=dt.UTC).timestamp())
    state = [
        "4ca123",
        "RYR9602 ",
        "Ireland",
        observed_timestamp,
        observed_timestamp,
        2.1,
        41.1,
        10_000.0,
        False,
        220.0,
        85.0,
        0.0,
        None,
        10_200.0,
        "1234",
        False,
        0,
    ]
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(200, {"time": observed_timestamp, "states": [state]}),
    )

    outcome = provider.fetch(
        _identity(callsign="RYR9602", icao24="4ca123"),
        dt.datetime(2026, 7, 22, 8, 45),
    )

    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.latitude == 41.1
    assert outcome.observation.altitude_m == 10_000
    assert outcome.observation.status == "active"

    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(429, {}, {"X-Rate-Limit-Retry-After-Seconds": "91"}),
    )
    assert isinstance(
        provider.fetch(_identity(icao24="4ca123"), dt.datetime.now()), OperationalRateLimited
    )


def test_opensky_rejects_future_position_timestamp(monkeypatch) -> None:
    provider = OpenSkyOperationalFlightProvider("https://opensky.test/api", 4)
    now = dt.datetime(2026, 7, 22, 8, 45)
    future = int((now.replace(tzinfo=dt.UTC) + dt.timedelta(minutes=6)).timestamp())
    state = [
        "4ca123",
        "RYR9602 ",
        "Ireland",
        future,
        future,
        2.1,
        41.1,
        10_000.0,
        False,
        220.0,
        85.0,
        0.0,
        None,
        10_200.0,
        "1234",
        False,
        0,
    ]
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(200, {"time": future, "states": [state]}),
    )

    outcome = provider.fetch(_identity(callsign="RYR9602", icao24="4ca123"), now)

    assert isinstance(outcome, OperationalUnavailable)
    assert outcome.reason == "invalid_observation"


def test_aerodatabox_maps_full_flight_contract(monkeypatch) -> None:
    provider = AeroDataBoxOperationalFlightProvider(
        "secret", "https://aerodatabox.test", "aerodatabox.test", 4
    )
    payload = [
        {
            "number": "FR 9602",
            "callSign": "RYR9602",
            "status": "EnRoute",
            "lastUpdatedUtc": "2026-07-22T08:45:00Z",
            "departure": {
                "airport": {"iata": "MAD"},
                "scheduledTime": {
                    "utc": "2026-07-22T08:30:00Z",
                    "local": "2026-07-22T10:30:00+02:00",
                },
                "revisedTime": {
                    "utc": "2026-07-22T08:43:00Z",
                    "local": "2026-07-22T10:43:00+02:00",
                },
                "terminal": "1",
                "gate": "B12",
                "quality": ["Basic"],
            },
            "arrival": {
                "airport": {"iata": "FCO"},
                "scheduledTime": {
                    "utc": "2026-07-22T10:55:00Z",
                    "local": "2026-07-22T12:55:00+02:00",
                },
                "revisedTime": {
                    "utc": "2026-07-22T11:05:00Z",
                    "local": "2026-07-22T13:05:00+02:00",
                },
                "terminal": "3",
                "gate": "E8",
                "quality": ["Basic"],
            },
            "aircraft": {"reg": "EI-TEST", "modeS": "4CA123", "model": "Boeing 737-800"},
            "location": {
                "reportedAtUtc": "2026-07-22T08:45:00Z",
                "lat": 41.1,
                "lon": 2.1,
                "altitude": {"meter": 10000},
                "groundSpeed": {"meterPerSecond": 220},
                "trueTrack": {"deg": 85},
            },
        }
    ]
    monkeypatch.setattr(provider._session, "get", lambda *args, **kwargs: _Response(200, payload))

    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 46))

    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.status == "active"
    assert outcome.observation.registration == "EI-TEST"
    assert outcome.observation.arrival_delay_minutes == 10
    assert outcome.observation.speed_mps == 220


def test_flightaware_maps_aeroapi_flight(monkeypatch) -> None:
    provider = FlightAwareOperationalFlightProvider("secret", "https://aeroapi.test/aeroapi", 4)
    payload = {
        "flights": [
            {
                "fa_flight_id": "FR9602-1",
                "ident_iata": "FR9602",
                "ident_icao": "RYR9602",
                "origin": {"code_iata": "MAD"},
                "destination": {"code_iata": "FCO"},
                "status": "En Route",
                "cancelled": False,
                "diverted": False,
                "scheduled_out": "2026-07-22T08:30:00Z",
                "estimated_out": "2026-07-22T08:40:00Z",
                "actual_out": "2026-07-22T08:43:00Z",
                "scheduled_in": "2026-07-22T10:55:00Z",
                "estimated_in": "2026-07-22T11:05:00Z",
                "departure_delay": 780,
                "arrival_delay": 600,
                "terminal_origin": "1",
                "gate_origin": "B12",
                "terminal_destination": "3",
                "gate_destination": "E8",
                "registration": "EI-TEST",
                "aircraft_type": "B738",
                "last_position": {
                    "fa_flight_id": "FR9602-1",
                    "timestamp": "2026-07-22T08:45:00Z",
                    "latitude": 41.1,
                    "longitude": 2.1,
                    "altitude": 328,
                    "groundspeed": 428,
                    "heading": 85,
                },
            }
        ]
    }
    monkeypatch.setattr(provider._session, "get", lambda *args, **kwargs: _Response(200, payload))

    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 46))

    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.altitude_m == pytest.approx(9997.44)
    assert outcome.observation.speed_mps == pytest.approx(220.18, rel=1e-3)
    assert outcome.observation.departure_delay_minutes == 13


def test_adsb_exchange_maps_aircraft_and_requires_identifier(monkeypatch) -> None:
    provider = AdsbExchangeOperationalFlightProvider("secret", "https://adsb.test/v2", 4)
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(
            200,
            {
                "ac": [
                    {
                        "hex": "4ca123",
                        "flight": "RYR9602 ",
                        "lat": 41.1,
                        "lon": 2.1,
                        "alt_baro": 32800,
                        "gs": 428,
                        "track": 85,
                        "r": "EI-TEST",
                        "t": "B738",
                    }
                ]
            },
        ),
    )

    outcome = provider.fetch(_identity(icao24="4ca123"), dt.datetime(2026, 7, 22, 8, 46))

    assert isinstance(outcome, OperationalObserved)
    assert outcome.observation.status == "active"
    assert outcome.observation.altitude_m == pytest.approx(9997.44)
    assert isinstance(provider.fetch(_identity(), dt.datetime.now()), OperationalNoCoverage)


@pytest.mark.parametrize(
    "provider",
    [
        OpenSkyOperationalFlightProvider("https://opensky.test/api", 4),
        AeroDataBoxOperationalFlightProvider(
            "secret", "https://aerodatabox.test", "aerodatabox.test", 4
        ),
        FlightAwareOperationalFlightProvider("secret", "https://aeroapi.test/aeroapi", 4),
        AdsbExchangeOperationalFlightProvider("secret", "https://adsb.test/v2", 4),
    ],
)
def test_get_adapters_honor_remote_retry_after(monkeypatch, provider) -> None:
    monkeypatch.setattr(
        provider._session,
        "get",
        lambda *args, **kwargs: _Response(
            429,
            {},
            {"X-Rate-Limit-Retry-After-Seconds": "91"},
        ),
    )

    outcome = provider.fetch(
        _identity(callsign="RYR9602", icao24="4ca123"),
        dt.datetime(2026, 7, 22, 8, 45),
    )

    assert isinstance(outcome, OperationalRateLimited)
    assert outcome.retry_after_seconds == 91


def test_amadeus_token_quota_failure_does_not_attempt_flight_call(monkeypatch) -> None:
    provider = AmadeusOperationalFlightProvider("client", "secret", "https://test.api", 4)
    flight_calls = 0

    def fake_get(*args, **kwargs):
        nonlocal flight_calls
        flight_calls += 1
        return _Response(200, {})

    monkeypatch.setattr(
        provider._session,
        "post",
        lambda *args, **kwargs: _Response(429, {}, {"Retry-After": "75"}),
    )
    monkeypatch.setattr(provider._session, "get", fake_get)

    outcome = provider.fetch(_identity(), dt.datetime(2026, 7, 22, 8, 45))

    assert isinstance(outcome, OperationalRateLimited)
    assert outcome.retry_after_seconds == 75
    assert flight_calls == 0


@pytest.mark.parametrize("status", [401, 402, 403, 500])
def test_paid_provider_remote_failures_do_not_raise(monkeypatch, status: int) -> None:
    provider = AdsbExchangeOperationalFlightProvider("secret", "https://adsb.test/v2", 4)
    monkeypatch.setattr(provider._session, "get", lambda *args, **kwargs: _Response(status, {}))

    outcome = provider.fetch(_identity(icao24="4ca123"), dt.datetime.now())

    assert isinstance(outcome, OperationalUnavailable)
    if status == 402:
        assert outcome.reason == "payment_required"
