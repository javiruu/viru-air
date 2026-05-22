from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.door_to_door.providers.base import DoorToDoorProviderQuery
from app.door_to_door.providers.google_routes import GoogleRoutesProvider
from app.door_to_door.schemas import DoorToDoorFlightOut, DoorToDoorLocation, DoorToDoorPreferences

MADRID = ZoneInfo("Europe/Madrid")


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _query() -> DoorToDoorProviderQuery:
    return DoorToDoorProviderQuery(
        origin=DoorToDoorLocation(type="city", label="Almería", lat=36.834, lng=-2.463),
        final_destination=DoorToDoorLocation(type="city", label="Treviso centro"),
        preferences=DoorToDoorPreferences(
            min_airport_buffer_minutes=120,
            max_price=None,
            passengers=1,
            luggage="cabin",
            allow_bus=True,
            allow_train=True,
            allow_rideshare=True,
            allow_shuttle=True,
            allow_taxi=False,
            allow_car=True,
            public_transport_only=False,
            sort_by="best_balance",
        ),
        flight=DoorToDoorFlightOut(
            origin_airport="AGP",
            destination_airport="TSF",
            departure_at=datetime(2026, 6, 14, 14, 20, tzinfo=MADRID),
            arrival_at=datetime(2026, 6, 14, 16, 55, tzinfo=MADRID),
            flight_time_confidence="estimated",
        ),
        checked_at=datetime(2026, 5, 20, 10, 0, tzinfo=MADRID),
    )


def test_google_routes_provider_disabled_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES", "1")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    provider = GoogleRoutesProvider()

    result = asyncio.run(provider.search(_query()))

    assert result == []
    health = asyncio.run(provider.healthcheck())
    assert health.status == "missing_api_key"


def test_google_routes_provider_normalizes_duration_distance_without_price(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")

    call_counter = {"count": 0}

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        call_counter["count"] += 1
        return _FakeResponse(200, {"routes": [{"duration": "7200s", "distanceMeters": 198000}]})

    monkeypatch.setattr("app.door_to_door.providers.google_routes.requests.post", fake_post)

    provider = GoogleRoutesProvider()
    options = asyncio.run(provider.search(_query()))

    assert len(options) == 1
    option = options[0]
    assert option.source_types == ["api"]
    assert option.total_price_min is None
    assert option.total_price_max is None
    assert option.legs[0].duration_minutes == 120
    assert option.legs[0].distance_meters == 198000
    assert option.sources[0].provider == "google_routes"
    assert option.sources[0].confidence == "live"
    warnings = provider.consume_warnings()
    assert any(warning.code == "UNCONFIRMED_PRICE" for warning in warnings)
    assert call_counter["count"] == 2


def test_google_routes_provider_uses_cache(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")

    call_counter = {"count": 0}

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        call_counter["count"] += 1
        return _FakeResponse(200, {"routes": [{"duration": "5400s", "distanceMeters": 166000}]})

    monkeypatch.setattr("app.door_to_door.providers.google_routes.requests.post", fake_post)

    provider = GoogleRoutesProvider()
    first = asyncio.run(provider.search(_query()))
    second = asyncio.run(provider.search(_query()))

    assert first
    assert second
    assert second[0].sources[0].confidence == "cached"
    assert call_counter["count"] == 2
