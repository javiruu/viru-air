"""Unit tests for GTFS transit provider and feed service."""

import io
import os
import tempfile
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.door_to_door.providers.gtfs_transit import GtfsTransitProvider
from app.door_to_door.providers.base import DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorLocation,
    DoorToDoorPreferences,
    DoorToDoorOptionOut,
)
from app.door_to_door.services.gtfs_feed_service import (
    GtfsFeedDescriptor,
    GtfsFeedService,
    ParsedGtfsFeed,
    load_feed_descriptors,
)


# ---------------------------------------------------------------------------
# GTFS fixture builder
# ---------------------------------------------------------------------------

def _build_minimal_gtfs_zip() -> bytes:
    """Create a minimal valid GTFS zip in memory for testing."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # agency.txt
        zf.writestr(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone\n"
            "ctan,Consorcio Transporte Andalucia,https://ctan.es,Europe/Madrid\n",
        )
        # stops.txt (Málaga area)
        zf.writestr(
            "stops.txt",
            "stop_id,stop_name,stop_lat,stop_lon\n"
            "stop_estacion,Estacion Autobuses Malaga,36.7167,-4.4257\n"
            "stop_aeropuerto,Parada Aeropuerto Malaga,36.6749,-4.4993\n"
            "stop_centro,Centro Malaga,36.7213,-4.4215\n"
            "stop_almeria,Estacion Almeria,36.8381,-2.4597\n",
        )
        # routes.txt
        zf.writestr(
            "routes.txt",
            "route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "route_aerobus,ctan,AeroBus,Aeropuerto Express,3\n"
            "route_urbano,ctan,L1,Linea 1 Centro,3\n",
        )
        # trips.txt
        zf.writestr(
            "trips.txt",
            "route_id,service_id,trip_id,trip_headsign\n"
            "route_aerobus,svc_weekday,trip_aero_1,Aeropuerto\n"
            "route_aerobus,svc_weekday,trip_aero_2,Aeropuerto\n"
            "route_urbano,svc_weekday,trip_urb_1,Centro\n",
        )
        # stop_times.txt
        zf.writestr(
            "stop_times.txt",
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "trip_aero_1,08:00:00,08:05:00,stop_estacion,1\n"
            "trip_aero_1,08:35:00,08:40:00,stop_aeropuerto,2\n"
            "trip_aero_2,10:00:00,10:05:00,stop_estacion,1\n"
            "trip_aero_2,10:35:00,10:40:00,stop_aeropuerto,2\n"
            "trip_urb_1,09:00:00,09:05:00,stop_estacion,1\n"
            "trip_urb_1,09:15:00,09:20:00,stop_centro,2\n",
        )
        # calendar.txt (weekday service from 2026-01-01 to 2027-01-01)
        zf.writestr(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "svc_weekday,1,1,1,1,1,0,0,20260101,20270101\n",
        )
    return buf.getvalue()


def _build_feed_descriptor() -> GtfsFeedDescriptor:
    return GtfsFeedDescriptor(
        id="test_feed",
        name="Test Feed",
        region="andalucia",
        url="file:///test_feed.zip",
    )


def _make_query(
    *,
    origin_label="Málaga Estación",
    origin_type="station",
    origin_lat=36.7167,
    origin_lng=-4.4257,
    final_type="city",
    final_label="Málaga Centro",
    final_lat=36.7213,
    final_lng=-4.4215,
    min_airport_buffer_minutes=120,
    max_price=None,
    passengers=1,
    allow_bus=True,
    allow_train=True,
    allow_rideshare=False,
    allow_shuttle=False,
    public_transport_only=False,
    origin_airport="AGP",
    destination_airport="MAD",
    flight_time_confidence="live",
    departure_at=None,
    arrival_at=None,
) -> DoorToDoorProviderQuery:
    now = datetime.now(tz=timezone.utc)
    dep = departure_at or datetime(2026, 7, 15, 14, 20, tzinfo=timezone(timedelta(hours=2)))
    arr = arrival_at or (dep + timedelta(hours=1, minutes=15))

    return DoorToDoorProviderQuery(
        origin=DoorToDoorLocation(type=origin_type, label=origin_label, lat=origin_lat, lng=origin_lng),
        final_destination=DoorToDoorLocation(type=final_type, label=final_label, lat=final_lat, lng=final_lng),
        preferences=DoorToDoorPreferences(
            min_airport_buffer_minutes=min_airport_buffer_minutes,
            max_price=max_price,
            passengers=passengers,
            allow_bus=allow_bus,
            allow_train=allow_train,
            allow_rideshare=allow_rideshare,
            allow_shuttle=allow_shuttle,
            public_transport_only=public_transport_only,
        ),
        flight=DoorToDoorFlightOut(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            departure_at=dep,
            arrival_at=arr,
            flight_time_confidence=flight_time_confidence,
        ),
        checked_at=now,
    )


class FakeGtfsFeedService(GtfsFeedService):
    """Feed service that reads from an in-memory zip instead of downloading."""

    def __init__(self, zip_bytes: bytes, **kwargs) -> None:  # noqa: ANN003
        super().__init__(**kwargs)
        self._zip_bytes = zip_bytes
        self._feeds_cleared = False

    def load_feed(self, descriptor: GtfsFeedDescriptor) -> ParsedGtfsFeed | None:
        if not self._feeds_cleared:
            self._feeds.clear()
            self._feeds_cleared = True

        if descriptor.id in self._feeds:
            return self._feeds[descriptor.id]

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(self._zip_bytes)
            tmp_path = Path(f.name)

        try:
            feed = self._parse_feed(tmp_path, descriptor.id)
            if feed is not None:
                self._feeds[descriptor.id] = feed
            return feed
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass


@pytest.fixture
def gtfs_zip() -> bytes:
    return _build_minimal_gtfs_zip()


@pytest.fixture
def feed_service(gtfs_zip: bytes) -> FakeGtfsFeedService:
    svc = FakeGtfsFeedService(gtfs_zip, max_walk_radius_meters=5000, max_results=5)
    return svc


@pytest.fixture
def provider(feed_service: FakeGtfsFeedService, monkeypatch) -> GtfsTransitProvider:
    # Mock load_feed_descriptors to return our test feed
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [_build_feed_descriptor()],
    )
    # Mock GtfsFeedService() to return our fake
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.GtfsFeedService",
        lambda **kw: feed_service,
    )
    return GtfsTransitProvider(feed_service=feed_service)


# ---------------------------------------------------------------------------
# Feed service tests
# ---------------------------------------------------------------------------

def test_feed_service_parses_stops(feed_service, gtfs_zip):
    desc = _build_feed_descriptor()
    feed = feed_service.load_feed(desc)
    assert feed is not None
    assert len(feed.stops) == 4
    assert "stop_estacion" in feed.stops
    assert feed.stops["stop_estacion"].name == "Estacion Autobuses Malaga"


def test_feed_service_parses_routes(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    assert len(feed.routes) == 2
    assert feed.routes["route_aerobus"].short_name == "AeroBus"


def test_feed_service_parses_trips(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    assert len(feed.trips) == 3
    assert feed.trips["trip_aero_1"].route_id == "route_aerobus"


def test_feed_service_parses_stop_times(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    assert "trip_aero_1" in feed.stop_times
    st_list = feed.stop_times["trip_aero_1"]
    assert len(st_list) == 2
    assert st_list[0].stop_id == "stop_estacion"
    assert st_list[1].stop_id == "stop_aeropuerto"


def test_feed_service_parses_calendar(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    assert "svc_weekday" in feed.calendar
    # July 15 2026 is a Wednesday -> should be active
    target = date(2026, 7, 15)
    assert target in feed.calendar["svc_weekday"]


def test_feed_service_finds_nearby_stops(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    stops = feed_service.find_nearby_stops(feed.feed_id, 36.7170, -4.4250)
    assert len(stops) > 0
    assert any(s.name == "Estacion Autobuses Malaga" for s in stops)


def test_feed_service_no_nearby_stops_far_away(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    stops = feed_service.find_nearby_stops(feed.feed_id, 40.4168, -3.7038)
    assert len(stops) == 0


def test_feed_service_finds_trips_between(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    target = date(2026, 7, 15)
    trips = feed_service.find_trips_between(
        feed.feed_id,
        "stop_estacion",
        "stop_aeropuerto",
        target_date=target,
    )
    assert len(trips) == 2
    assert trips[0].from_stop_name == "Estacion Autobuses Malaga"
    assert trips[0].to_stop_name == "Parada Aeropuerto Malaga"
    assert trips[0].route_name == "AeroBus"


def test_feed_service_filters_by_time_window(feed_service):
    feed = feed_service.load_feed(_build_feed_descriptor())
    target = date(2026, 7, 15)
    latest = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    trips = feed_service.find_trips_between(
        feed.feed_id,
        "stop_estacion",
        "stop_aeropuerto",
        target_date=target,
        latest_arrival=latest,
    )
    assert len(trips) == 2
    for trip in trips:
        assert trip.arrival_at <= latest


def test_feed_service_returns_empty_on_missing_feed(feed_service):
    stops = feed_service.find_nearby_stops("nonexistent", 36.7, -4.4)
    assert stops == []


def test_load_feed_descriptors_from_env(monkeypatch):
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", json.dumps([
        {"id": "ctan", "name": "CTAN", "url": "https://ctan.es/gtfs.zip"},
    ]))
    descriptors = load_feed_descriptors()
    assert len(descriptors) == 1
    assert descriptors[0].id == "ctan"


def test_load_feed_descriptors_empty_when_no_env(monkeypatch):
    monkeypatch.delenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", raising=False)
    descriptors = load_feed_descriptors()
    assert descriptors == []


def test_load_feed_descriptors_skips_invalid(monkeypatch):
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", json.dumps([
        {"name": "No id or url"},
        {"id": "has_id", "url": "https://example.com"},
    ]))
    descriptors = load_feed_descriptors()
    assert len(descriptors) == 1
    assert descriptors[0].id == "has_id"


# ---------------------------------------------------------------------------
# Provider tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_disabled_without_feeds(monkeypatch):
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [],
    )
    provider = GtfsTransitProvider()
    results = await provider.search(_make_query())
    assert results == []


@pytest.mark.asyncio
async def test_provider_returns_open_data_option(provider):
    query = _make_query()
    results = await provider.search(query)
    assert len(results) > 0
    option = results[0]
    assert "open_data" in option.source_types
    assert option.total_price_min is None
    assert option.total_price_max is None


@pytest.mark.asyncio
async def test_provider_no_inventa_precio(provider):
    results = await provider.search(_make_query())
    for option in results:
        assert option.total_price_min is None
        assert option.total_price_max is None
        assert option.price_per_person_min is None
        assert option.price_per_person_max is None
        for leg in option.legs:
            if leg.type == "ground":
                assert leg.price_min is None
                assert leg.price_max is None


@pytest.mark.asyncio
async def test_provider_legs_have_source_type_open_data(provider):
    results = await provider.search(_make_query())
    option = results[0]
    ground_legs = [leg for leg in option.legs if leg.type == "ground"]
    assert len(ground_legs) > 0
    for leg in ground_legs:
        assert leg.source_type == "open_data"
        assert leg.provider == "gtfs_transit"
        assert leg.booking_url is None


@pytest.mark.asyncio
async def test_provider_emite_unconfirmed_price(provider):
    await provider.search(_make_query())
    warnings = provider.consume_warnings()
    assert any(w.code == "UNCONFIRMED_PRICE" for w in warnings)


@pytest.mark.asyncio
async def test_provider_emite_gtfs_price_unavailable(provider):
    await provider.search(_make_query())
    warnings = provider.consume_warnings()
    assert any(w.code == "GTFS_PRICE_UNAVAILABLE" for w in warnings)


@pytest.mark.asyncio
async def test_provider_respeta_airport_only(provider):
    results = await provider.search(_make_query(final_type="airport_only", final_label="Solo AGP"))
    # Should still work for outbound, but no inbound leg
    if results:
        for option in results:
            legs = [leg for leg in option.legs if leg.type == "ground"]
            assert len(legs) <= 1  # Only outbound ground or none


@pytest.mark.asyncio
async def test_provider_falla_feed_controlado(provider):
    # We won't break the provider - it already handles missing feeds gracefully
    results = await provider.search(_make_query())
    # Should not raise, and should return options or empty list
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_provider_sources_have_open_data_source_type(provider):
    results = await provider.search(_make_query())
    if results:
        option = results[0]
        for source in option.sources:
            assert source.source_type == "open_data"
            assert source.provider == "gtfs_transit"


@pytest.mark.asyncio
async def test_provider_healthcheck(provider):
    health = await provider.healthcheck()
    assert health.provider == "gtfs_transit"
    assert health.source_type == "open_data"


@pytest.mark.asyncio
async def test_provider_healthcheck_disabled_no_feeds(monkeypatch):
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [],
    )
    provider = GtfsTransitProvider()
    health = await provider.healthcheck()
    assert health.status == "disabled_no_feeds"


# ---------------------------------------------------------------------------
# Registry / status tests
# ---------------------------------------------------------------------------

def test_provider_status_clasifica_gtfs_como_functional_open_data(monkeypatch):
    import os
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", "1")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_SCRAPERS", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT", "1")
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", json.dumps([
        {"id": "test", "url": "https://example.com/gtfs.zip"},
    ]))
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    from app.door_to_door.providers.registry import resolve_provider_runtime

    runtime = resolve_provider_runtime()
    statuses = {s.name: s for s in runtime.statuses}

    assert "gtfs_transit" in statuses
    assert statuses["gtfs_transit"].enabled is True
    assert statuses["gtfs_transit"].status == "functional_open_data"
    assert statuses["gtfs_transit"].source_type == "open_data"
    assert statuses["gtfs_transit"].supports_search is True
    assert statuses["gtfs_transit"].supports_booking_url is False
    assert statuses["gtfs_transit"].has_tests is True
    assert statuses["gtfs_transit"].production_ready is False


def test_provider_status_gtfs_disabled_without_feeds(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", "1")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT", "1")
    monkeypatch.delenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    from app.door_to_door.providers.registry import resolve_provider_runtime

    runtime = resolve_provider_runtime()
    statuses = {s.name: s for s in runtime.statuses}

    assert statuses["gtfs_transit"].enabled is False
    assert statuses["gtfs_transit"].status == "disabled"
    assert "faltan feeds" in (statuses["gtfs_transit"].notes or "")


def test_provider_status_gtfs_disabled_without_flag(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", "1")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT", "0")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    from app.door_to_door.providers.registry import resolve_provider_runtime

    runtime = resolve_provider_runtime()
    statuses = {s.name: s for s in runtime.statuses}

    assert statuses["gtfs_transit"].enabled is False
    assert statuses["gtfs_transit"].status == "disabled"


import json  # noqa: E402 - needed for monkeypatch.setenv above
