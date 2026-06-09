"""Unit tests for Navitia transport provider."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.door_to_door.providers.navitia import (
    NavitiaProvider,
    _navitia_mode_to_d2d,
    _parse_journey,
    _parse_navitia_datetime,
    _parse_section,
    _parse_wkt_polygon,
    _point_in_wkt_polygon,
)
from app.door_to_door.providers.base import DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorLocation,
    DoorToDoorPreferences,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_query(
    *,
    origin_label="Malaga Estacion",
    origin_type="station",
    origin_lat=36.7167,
    origin_lng=-4.4257,
    final_type="city",
    final_label="Malaga Centro",
    final_lat=36.7213,
    final_lng=-4.4215,
    min_airport_buffer_minutes=120,
    origin_airport="AGP",
    destination_airport="MAD",
    flight_time_confidence="live",
    departure_at=None,
    arrival_at=None,
) -> DoorToDoorProviderQuery:
    dep = departure_at or datetime(2026, 7, 15, 14, 20, tzinfo=timezone(timedelta(hours=2)))
    arr = arrival_at or (dep + timedelta(hours=1, minutes=15))

    return DoorToDoorProviderQuery(
        origin=DoorToDoorLocation(type=origin_type, label=origin_label, lat=origin_lat, lng=origin_lng),
        final_destination=DoorToDoorLocation(type=final_type, label=final_label, lat=final_lat, lng=final_lng),
        preferences=DoorToDoorPreferences(min_airport_buffer_minutes=min_airport_buffer_minutes),
        flight=DoorToDoorFlightOut(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            departure_at=dep,
            arrival_at=arr,
            flight_time_confidence=flight_time_confidence,
        ),
        checked_at=datetime.now(tz=dep.tzinfo),
    )


# ---------------------------------------------------------------------------
# Fixtures: mocked Navitia API responses
# ---------------------------------------------------------------------------

def _make_coverage_response() -> dict:
    """Mock Navitia /coverage response with Spain and Italy regions."""
    return {
        "regions": [
            {
                "id": "es-malaga",
                "name": "Malaga",
                "shape": "POLYGON((-4.6 36.6, -4.3 36.6, -4.3 36.8, -4.6 36.8, -4.6 36.6))",
                "admin_level": 8,
                "parent_region_id": "es",
            },
            {
                "id": "es",
                "name": "Spain",
                "shape": "POLYGON((-10.0 35.0, 5.0 35.0, 5.0 44.0, -10.0 44.0, -10.0 35.0))",
                "admin_level": 2,
            },
            {
                "id": "it-veneto",
                "name": "Veneto",
                "shape": "POLYGON((10.5 44.5, 13.0 44.5, 13.0 46.5, 10.5 46.5, 10.5 44.5))",
                "admin_level": 4,
                "parent_region_id": "it",
            },
            {
                "id": "it",
                "name": "Italy",
                "shape": "POLYGON((6.0 35.0, 19.0 35.0, 19.0 47.0, 6.0 47.0, 6.0 35.0))",
                "admin_level": 2,
            },
        ]
    }


def _make_journey_response() -> dict:
    """Mock Navitia /coverage/{id}/journeys response."""
    return {
        "journeys": [
            {
                "duration": 2400,  # 40 minutes
                "departure_date_time": "20260715T110000",
                "arrival_date_time": "20260715T114000",
                "nb_transfers": 0,
                "sections": [
                    {
                        "mode": "walking",
                        "from": {"name": "Estacion Autobuses"},
                        "to": {"name": "Parada Bus Aeropuerto"},
                        "departure_date_time": "20260715T110000",
                        "arrival_date_time": "20260715T110500",
                        "duration": 300,
                        "display_informations": {},
                    },
                    {
                        "mode": "bus",
                        "from": {"name": "Parada Bus Aeropuerto"},
                        "to": {"name": "Aeropuerto Malaga"},
                        "departure_date_time": "20260715T110500",
                        "arrival_date_time": "20260715T113500",
                        "duration": 1800,
                        "display_informations": {
                            "headsign": "Aeropuerto",
                            "network": "EMT",
                            "commercial_mode": "Bus",
                        },
                    },
                    {
                        "mode": "walking",
                        "from": {"name": "Aeropuerto Malaga"},
                        "to": {"name": "Terminal T3"},
                        "departure_date_time": "20260715T113500",
                        "arrival_date_time": "20260715T114000",
                        "duration": 300,
                        "display_informations": {},
                    },
                ],
            },
            {
                "duration": 3000,  # 50 minutes
                "departure_date_time": "20260715T110000",
                "arrival_date_time": "20260715T115000",
                "nb_transfers": 1,
                "sections": [
                    {
                        "mode": "bus",
                        "from": {"name": "Estacion Autobuses"},
                        "to": {"name": "Aeropuerto Malaga"},
                        "departure_date_time": "20260715T141000",
                        "arrival_date_time": "20260715T150000",
                        "duration": 3000,
                        "display_informations": {
                            "headsign": "Aeropuerto",
                            "network": "EMT",
                        },
                    },
                ],
            },
        ]
    }


def _make_empty_journey_response() -> dict:
    return {"journeys": []}


# ---------------------------------------------------------------------------
# Provider: disabled states
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_disabled_without_flag(monkeypatch):
    """Provider returns empty when DOOR_TO_DOOR_ENABLE_NAVITIA is false."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "false")
    provider = NavitiaProvider()
    results = await provider.search(_make_query())
    assert results == []


@pytest.mark.asyncio
async def test_provider_disabled_without_api_key(monkeypatch):
    """Provider returns empty and emits warning when API key is missing."""
    monkeypatch.delenv("NAVITIA_API_KEY", raising=False)
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")
    provider = NavitiaProvider()
    results = await provider.search(_make_query())
    warnings = provider.consume_warnings()
    assert results == []
    assert any(w.code == "NAVITIA_API_KEY_MISSING" for w in warnings)


# ---------------------------------------------------------------------------
# Provider: mocked real search
# ---------------------------------------------------------------------------

class _FakeHttpxResponse:
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def json(self) -> dict:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.mark.asyncio
async def test_provider_returns_options_with_mocked_api(monkeypatch):
    """Provider returns DoorToDoorOptionOut when Navitia API responds with journeys."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    call_count = 0

    def fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "/coverage" in str(url) and "journeys" not in str(url):
            return _FakeHttpxResponse(_make_coverage_response())
        return _FakeHttpxResponse(_make_journey_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        results = await provider.search(_make_query())

    assert len(results) > 0
    option = results[0]
    assert option.status == "real_result"
    assert "api" in option.source_types
    assert option.total_price_min is None
    # Should have outbound + flight + inbound legs
    assert len(option.legs) >= 2  # at minimum outbound + flight


@pytest.mark.asyncio
async def test_provider_no_price_invented(monkeypatch):
    """Navitia provider never invents prices."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    def fake_get(url, **kwargs):
        if "/coverage" in str(url) and "journeys" not in str(url):
            return _FakeHttpxResponse(_make_coverage_response())
        return _FakeHttpxResponse(_make_journey_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        results = await provider.search(_make_query())

    for option in results:
        assert option.total_price_min is None
        assert option.total_price_max is None
        for leg in option.legs:
            if leg.type == "ground":
                assert leg.price_min is None
                assert leg.price_max is None


@pytest.mark.asyncio
async def test_provider_emits_no_coverage_when_no_match(monkeypatch):
    """When no coverage contains the origin point, emit NAVITIA_NO_COVERAGE."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    # Coverage response with regions that don't contain the origin
    far_coverages = {
        "regions": [
            {
                "id": "fr-idf",
                "name": "Paris",
                "shape": "POLYGON((2.0 48.5, 2.7 48.5, 2.7 49.0, 2.0 49.0, 2.0 48.5))",
                "admin_level": 4,
            },
        ]
    }

    def fake_get(url, **kwargs):
        if "/coverage" in str(url) and "journeys" not in str(url):
            return _FakeHttpxResponse(far_coverages)
        return _FakeHttpxResponse(_make_empty_journey_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        results = await provider.search(_make_query())

    warnings = provider.consume_warnings()
    assert results == []
    assert any(w.code == "NAVITIA_NO_COVERAGE" for w in warnings)


@pytest.mark.asyncio
async def test_provider_emits_no_journeys_when_coverage_has_no_routes(monkeypatch):
    """When coverage matches but no journeys found, emit NAVITIA_NO_JOURNEYS."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    def fake_get(url, **kwargs):
        if "/coverage" in str(url) and "journeys" not in str(url):
            return _FakeHttpxResponse(_make_coverage_response())
        return _FakeHttpxResponse(_make_empty_journey_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        results = await provider.search(_make_query())

    warnings = provider.consume_warnings()
    assert results == []
    assert any(w.code == "NAVITIA_NO_JOURNEYS" for w in warnings)


@pytest.mark.asyncio
async def test_provider_respects_airport_only(monkeypatch):
    """When final_destination type is airport_only, skip inbound search."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    def fake_get(url, **kwargs):
        if "/coverage" in str(url) and "journeys" not in str(url):
            return _FakeHttpxResponse(_make_coverage_response())
        return _FakeHttpxResponse(_make_journey_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        results = await provider.search(_make_query(final_type="airport_only"))

    if results:
        for option in results:
            ground_legs = [leg for leg in option.legs if leg.type == "ground"]
            # Only outbound ground legs (no inbound)
            assert len(ground_legs) <= 3  # outbound sections


@pytest.mark.asyncio
async def test_provider_sources_have_api_source_type(monkeypatch):
    """All sources should have source_type='api'."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    def fake_get(url, **kwargs):
        if "/coverage" in str(url) and "journeys" not in str(url):
            return _FakeHttpxResponse(_make_coverage_response())
        return _FakeHttpxResponse(_make_journey_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        results = await provider.search(_make_query())

    if results:
        for option in results:
            for source in option.sources:
                assert source.source_type == "api"
                assert source.provider == "navitia"


@pytest.mark.asyncio
async def test_provider_legs_have_api_source_type(monkeypatch):
    """Ground legs should have source_type='api'."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    def fake_get(url, **kwargs):
        if "/coverage" in str(url) and "journeys" not in str(url):
            return _FakeHttpxResponse(_make_coverage_response())
        return _FakeHttpxResponse(_make_journey_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        results = await provider.search(_make_query())

    if results:
        option = results[0]
        ground_legs = [leg for leg in option.legs if leg.type == "ground"]
        assert len(ground_legs) > 0
        for leg in ground_legs:
            assert leg.source_type == "api"
            assert leg.provider == "navitia"


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_healthcheck_ok_with_key(monkeypatch):
    """Healthcheck returns ok when API key and flag are set."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    def fake_get(url, **kwargs):
        return _FakeHttpxResponse(_make_coverage_response())

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        health = await provider.healthcheck()

    assert health.provider == "navitia"
    assert health.status == "ok"
    assert health.source_type == "api"
    assert health.confidence == "live"


@pytest.mark.asyncio
async def test_healthcheck_disabled_without_flag(monkeypatch):
    """Healthcheck returns disabled when flag is off."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "false")
    provider = NavitiaProvider()
    health = await provider.healthcheck()
    assert health.status == "disabled"


@pytest.mark.asyncio
async def test_healthcheck_missing_api_key(monkeypatch):
    """Healthcheck returns missing_api_key when key is not set."""
    monkeypatch.delenv("NAVITIA_API_KEY", raising=False)
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")
    provider = NavitiaProvider()
    health = await provider.healthcheck()
    assert health.status == "missing_api_key"


@pytest.mark.asyncio
async def test_healthcheck_no_coverages(monkeypatch):
    """Healthcheck returns no_coverages when API returns empty regions."""
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "true")

    def fake_get(url, **kwargs):
        return _FakeHttpxResponse({"regions": []})

    with patch("httpx.get", side_effect=fake_get):
        provider = NavitiaProvider()
        health = await provider.healthcheck()

    assert health.status == "no_coverages"


# ---------------------------------------------------------------------------
# Mode mapping
# ---------------------------------------------------------------------------

def test_navitia_mode_maps_correctly():
    assert _navitia_mode_to_d2d("bus") == "bus"
    assert _navitia_mode_to_d2d("train") == "train"
    assert _navitia_mode_to_d2d("walking") == "walking"
    assert _navitia_mode_to_d2d("street_network") == "walking"
    assert _navitia_mode_to_d2d("metro") == "bus"
    assert _navitia_mode_to_d2d("tram") == "bus"
    assert _navitia_mode_to_d2d("car") == "car"
    assert _navitia_mode_to_d2d("shuttle") == "shuttle"
    assert _navitia_mode_to_d2d("taxi") == "taxi"
    assert _navitia_mode_to_d2d("unknown_mode") == "bus"  # default fallback


# ---------------------------------------------------------------------------
# Datetime parsing
# ---------------------------------------------------------------------------

def test_parse_navitia_datetime_valid():
    result = _parse_navitia_datetime("20260715T143000")
    assert result == datetime(2026, 7, 15, 14, 30, 0)


def test_parse_navitia_datetime_no_seconds():
    result = _parse_navitia_datetime("20260715T1430")
    assert result == datetime(2026, 7, 15, 14, 30, 0)


def test_parse_navitia_datetime_invalid():
    assert _parse_navitia_datetime("") is None
    assert _parse_navitia_datetime("notadate") is None
    assert _parse_navitia_datetime("2026-07-15T14:30:00") is None  # wrong format


# ---------------------------------------------------------------------------
# Journey parsing
# ---------------------------------------------------------------------------

def test_parse_journey_valid_response():
    raw = {
        "duration": 2400,
        "departure_date_time": "20260715T140000",
        "arrival_date_time": "20260715T144000",
        "nb_transfers": 0,
        "sections": [
            {
                "mode": "bus",
                "from": {"name": "Origin"},
                "to": {"name": "Airport"},
                "departure_date_time": "20260715T140000",
                "arrival_date_time": "20260715T144000",
                "duration": 2400,
                "display_informations": {"headsign": "Airport", "network": "EMT"},
            }
        ],
    }
    journey = _parse_journey(raw)
    assert journey is not None
    assert journey.duration_seconds == 2400
    assert journey.transfers == 0
    assert len(journey.sections) == 1
    assert journey.sections[0].mode == "bus"
    assert journey.sections[0].route_name == "Airport"


def test_parse_journey_empty():
    assert _parse_journey({}) is None
    assert _parse_journey({"sections": []}) is None


def test_parse_section_valid():
    raw = {
        "mode": "train",
        "from": {"name": "Station A"},
        "to": {"name": "Station B"},
        "departure_date_time": "20260715T100000",
        "arrival_date_time": "20260715T103000",
        "duration": 1800,
        "display_informations": {"headsign": "City Center", "network": "Renfe"},
    }
    section = _parse_section(raw)
    assert section is not None
    assert section.mode == "train"
    assert section.from_name == "Station A"
    assert section.to_name == "Station B"
    assert section.route_name == "City Center"
    assert section.network == "Renfe"
    assert section.duration_seconds == 1800


def test_parse_section_empty():
    assert _parse_section({}) is None


# ---------------------------------------------------------------------------
# WKT polygon parsing and point-in-polygon
# ---------------------------------------------------------------------------

def test_parse_simple_polygon():
    wkt = "POLYGON((-4.6 36.6, -4.3 36.6, -4.3 36.8, -4.6 36.8, -4.6 36.6))"
    coords = _parse_wkt_polygon(wkt)
    assert coords is not None
    assert len(coords) == 5
    assert coords[0] == (-4.6, 36.6)
    assert coords[2] == (-4.3, 36.8)


def test_parse_polygon_invalid():
    assert _parse_wkt_polygon("") is None
    assert _parse_wkt_polygon("NOT A POLYGON") is None


def test_point_in_polygon_inside():
    wkt = "POLYGON((-4.6 36.6, -4.3 36.6, -4.3 36.8, -4.6 36.8, -4.6 36.6))"
    # Point roughly in the middle of the polygon
    assert _point_in_wkt_polygon(36.7, -4.45, wkt) is True


def test_point_in_polygon_outside():
    wkt = "POLYGON((-4.6 36.6, -4.3 36.6, -4.3 36.8, -4.6 36.8, -4.6 36.6))"
    # Point far outside
    assert _point_in_wkt_polygon(40.0, 0.0, wkt) is False


def test_point_in_polygon_malaga_inside_spain():
    """Malaga coords should be inside a Spain-wide polygon."""
    spain_wkt = "POLYGON((-10.0 35.0, 5.0 35.0, 5.0 44.0, -10.0 44.0, -10.0 35.0))"
    assert _point_in_wkt_polygon(36.72, -4.42, spain_wkt) is True


def test_point_in_polygon_treviso_inside_italy():
    """Treviso coords should be inside an Italy-wide polygon."""
    italy_wkt = "POLYGON((6.0 35.0, 19.0 35.0, 19.0 47.0, 6.0 47.0, 6.0 35.0))"
    assert _point_in_wkt_polygon(45.65, 12.20, italy_wkt) is True


def test_point_in_polygon_paris_outside_spain():
    """Paris coords should NOT be inside a Spain polygon."""
    spain_wkt = "POLYGON((-10.0 35.0, 5.0 35.0, 5.0 44.0, -10.0 44.0, -10.0 35.0))"
    assert _point_in_wkt_polygon(48.86, 2.35, spain_wkt) is False


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------

def test_provider_status_clasifica_navitia_como_functional_api(monkeypatch):
    """Registry classifies navitia as functional_api when enabled."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", "1")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_SCRAPERS", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "1")
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    from app.door_to_door.providers.registry import resolve_provider_runtime

    runtime = resolve_provider_runtime()
    statuses = {s.name: s for s in runtime.statuses}

    assert "navitia" in statuses
    assert statuses["navitia"].enabled is True
    assert statuses["navitia"].status == "functional_api"
    assert statuses["navitia"].source_type == "api"
    assert statuses["navitia"].supports_search is True
    assert statuses["navitia"].supports_booking_url is False
    assert statuses["navitia"].has_tests is True
    assert statuses["navitia"].production_ready is False


def test_provider_status_navitia_disabled_without_key(monkeypatch):
    """Navitia is disabled when NAVITIA_API_KEY is missing."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", "1")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "1")
    monkeypatch.delenv("NAVITIA_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    from app.door_to_door.providers.registry import resolve_provider_runtime

    runtime = resolve_provider_runtime()
    statuses = {s.name: s for s in runtime.statuses}

    assert statuses["navitia"].enabled is False
    assert statuses["navitia"].status == "disabled"
    assert "NAVITIA_API_KEY" in (statuses["navitia"].notes or "")


def test_provider_status_navitia_disabled_without_flag(monkeypatch):
    """Navitia is disabled when DOOR_TO_DOOR_ENABLE_NAVITIA is off."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", "1")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NAVITIA", "0")
    monkeypatch.setenv("NAVITIA_API_KEY", "test-key")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    from app.door_to_door.providers.registry import resolve_provider_runtime

    runtime = resolve_provider_runtime()
    statuses = {s.name: s for s in runtime.statuses}

    assert statuses["navitia"].enabled is False
    assert statuses["navitia"].status == "disabled"
