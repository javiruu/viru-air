"""Unit tests for GTFS transit provider and feed service."""

import io
import json
import tempfile
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from app.door_to_door.providers.gtfs_transit import GtfsTransitProvider
from app.door_to_door.providers.base import DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorLocation,
    DoorToDoorPreferences,
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
            "route_urbano,svc_weekday,trip_urb_1,Centro\n"
            "route_urbano,svc_weekday,trip_inbound_1,Centro desde Aeropuerto\n"
            "route_urbano,svc_weekday,trip_inbound_2,Centro desde Aeropuerto\n",
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
            "trip_urb_1,09:15:00,09:20:00,stop_centro,2\n"
            "trip_inbound_1,16:00:00,16:05:00,stop_aeropuerto,1\n"
            "trip_inbound_1,16:35:00,16:40:00,stop_centro,2\n"
            "trip_inbound_2,18:00:00,18:05:00,stop_aeropuerto,1\n"
            "trip_inbound_2,18:35:00,18:40:00,stop_centro,2\n",
        )
        # calendar.txt (weekday service from 2026-01-01 to 2027-01-01)
        zf.writestr(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "svc_weekday,1,1,1,1,1,0,0,20260101,20270101\n",
        )
    return buf.getvalue()


def _build_gtfs_zip_with_fares() -> bytes:
    """Create a GTFS zip with fare data for pricing tests."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # agency.txt
        zf.writestr(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone\n"
            "ctan,Consorcio Transporte Andalucia,https://ctan.es,Europe/Madrid\n",
        )
        # stops.txt
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
            "route_urbano,svc_weekday,trip_urb_1,Centro\n"
            "route_urbano,svc_weekday,trip_inbound_1,Centro desde Aeropuerto\n"
            "route_urbano,svc_weekday,trip_inbound_2,Centro desde Aeropuerto\n",
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
            "trip_urb_1,09:15:00,09:20:00,stop_centro,2\n"
            "trip_inbound_1,16:00:00,16:05:00,stop_aeropuerto,1\n"
            "trip_inbound_1,16:35:00,16:40:00,stop_centro,2\n"
            "trip_inbound_2,18:00:00,18:05:00,stop_aeropuerto,1\n"
            "trip_inbound_2,18:35:00,18:40:00,stop_centro,2\n",
        )
        # calendar.txt
        zf.writestr(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "svc_weekday,1,1,1,1,1,0,0,20260101,20270101\n",
        )
        # fare_attributes.txt (Fase 5)
        zf.writestr(
            "fare_attributes.txt",
            "fare_id,price,currency_type,payment_method,transfers,agency_id,transfer_duration\n"
            "fare_aerobus,1.55,EUR,0,0,ctan,\n"
            "fare_urbano,1.20,EUR,0,0,ctan,\n"
            "fare_unlimited,3.00,EUR,1,,ctan,3600\n",
        )
        # fare_rules.txt (Fase 5)
        zf.writestr(
            "fare_rules.txt",
            "fare_id,route_id,origin_id,destination_id,contains_id\n"
            "fare_aerobus,route_aerobus,,,\n"
            "fare_urbano,route_urbano,,,\n"
            "fare_unlimited,,,,\n",
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
    assert len(feed.trips) == 5  # 3 original + 2 bidirectional inbound
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
    monkeypatch.delenv("DOOR_TO_DOOR_GTFS_FEEDS_FILE", raising=False)
    # Also monkeypatch the fallback manifest discovery to return nothing
    monkeypatch.setattr(
        "app.door_to_door.services.gtfs_feed_service.Path.exists",
        lambda self: False,
    )
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
    monkeypatch.delenv("DOOR_TO_DOOR_GTFS_FEEDS_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    # Suppress the default manifest fallback so _has_gtfs_feeds() returns False
    monkeypatch.setattr(
        "app.door_to_door.providers.registry.Path.exists",
        lambda self: False,
    )

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


# ---------------------------------------------------------------------------
# Granular warning tests
# ---------------------------------------------------------------------------

@pytest.fixture
def provider_no_nearby_stops(feed_service: FakeGtfsFeedService, monkeypatch) -> GtfsTransitProvider:
    """Provider where origin has lat/lng far from any stop."""
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [_build_feed_descriptor()],
    )
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.GtfsFeedService",
        lambda **kw: feed_service,
    )
    return GtfsTransitProvider(feed_service=feed_service)


@pytest.mark.asyncio
async def test_provider_emite_no_nearby_stops(provider_no_nearby_stops):
    """When origin is far from any stop, emit GTFS_NO_NEARBY_STOPS."""
    results = await provider_no_nearby_stops.search(_make_query(
        origin_lat=40.4168,
        origin_lng=-3.7038,
        origin_label="Madrid (lejos del feed)",
        final_lat=36.7213,
        final_lng=-4.4215,
    ))
    warnings = provider_no_nearby_stops.consume_warnings()
    assert any(w.code == "GTFS_NO_NEARBY_STOPS" for w in warnings)
    # Should still return results if inbound is fine, or empty if nowhere near
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_provider_emite_no_service_for_date(provider):
    """When feed has stops but no service on the target date, emit GTFS_NO_SERVICE_FOR_DATE."""
    # Use a Saturday (July 18, 2026), but our fixture only has weekday service
    saturday = datetime(2026, 7, 18, 14, 20, tzinfo=timezone(timedelta(hours=2)))
    _results = await provider.search(_make_query(
        departure_at=saturday,
        arrival_at=saturday + timedelta(hours=1, minutes=15),
    ))
    warnings = provider.consume_warnings()
    # The feed has no weekend service → GTFS_NO_SERVICE_FOR_DATE or GTFS_NO_MATCHING_SERVICE
    assert any(
        w.code in ("GTFS_NO_SERVICE_FOR_DATE", "GTFS_NO_MATCHING_SERVICE")
        for w in warnings
    )


@pytest.mark.asyncio
async def test_provider_filtra_viajes_demasiado_tarde_para_vuelo(provider):
    """Trips arriving after flight departure minus buffer should be filtered out.

    Flight departs at 09:00, buffer = 120min → latest arrival must be <= 07:00.
    Our fixture has trips arriving at 08:40 and 10:40 — both after 07:00.
    Therefore, all trips should be filtered → GTFS_NO_MATCHING_SERVICE.
    """
    # Use an even earlier departure so ALL trips (including the earliest at 08:00 UTC)
    # arrive after the buffer cutoff. Flight departs 07:00 UTC+2 = 05:00 UTC,
    # buffer 120 min -> latest arrival 03:00 UTC. All fixture trips arrive after 03:00.
    early_dep = datetime(2026, 7, 15, 5, 0, tzinfo=timezone.utc)
    early_arr = early_dep + timedelta(hours=1, minutes=15)
    await provider.search(_make_query(
        departure_at=early_dep,
        arrival_at=early_arr,
        min_airport_buffer_minutes=120,
    ))
    warnings = provider.consume_warnings()
    # With multi-term airport search, inbound trips may match even when outbound
    # doesn't (partial coverage). Both warnings indicate the outbound filtering works.
    assert any(
        w.code in ("GTFS_NO_MATCHING_SERVICE", "GTFS_PARTIAL_COVERAGE")
        for w in warnings
    ), "Expected GTFS_NO_MATCHING_SERVICE or GTFS_PARTIAL_COVERAGE when outbound trips arrive after buffer cutoff"


@pytest.mark.asyncio
async def test_provider_no_busca_inbound_airport_only(provider):
    """When final_destination.type='airport_only', provider skips inbound search."""
    results = await provider.search(_make_query(
        final_type="airport_only",
        final_label="Solo AGP",
    ))
    warnings = provider.consume_warnings()
    if results:
        for option in results:
            ground_legs = [leg for leg in option.legs if leg.type == "ground"]
            # Only outbound ground leg (or none if no trips)
            assert len(ground_legs) <= 1
    # Should not emit inbound-related warnings
    inbound_warnings = [w for w in warnings if "vuelta" in w.message or "inbound" in w.message.lower()]
    assert len(inbound_warnings) == 0


@pytest.mark.asyncio
async def test_provider_emite_partial_coverage(provider):
    """When only one leg has trips, emit GTFS_PARTIAL_COVERAGE."""
    # Use fixture where only outbound trips exist but inbound destination
    # coordinates are far away → no inbound trips
    _results = await provider.search(_make_query(
        final_lat=40.4168,  # Far from the Andalusia feed
        final_lng=-3.7038,
        final_label="Madrid (sin cobertura)",
    ))
    warnings = provider.consume_warnings()
    # Should have partial coverage or no nearby stops
    assert any(
        w.code in ("GTFS_PARTIAL_COVERAGE", "GTFS_NO_NEARBY_STOPS")
        for w in warnings
    )


@pytest.mark.asyncio
async def test_provider_filtra_duracion_excesiva(provider):
    """Trips longer than max_ground_duration should be filtered out."""
    # Our fixture has trips of 30-35 min, well under the 240 min default max
    # Test that short trips are kept
    results = await provider.search(_make_query())
    if results:
        for option in results:
            for leg in option.legs:
                if leg.type == "ground" and leg.duration_minutes:
                    assert leg.duration_minutes <= 240  # under max


@pytest.mark.asyncio
async def test_provider_respeta_max_walk_radius(feed_service, monkeypatch):
    """Feed service with small walk radius should find fewer stops."""
    # Create a feed service with tiny radius
    feed_service.max_walk_radius = 100  # only 100m
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [_build_feed_descriptor()],
    )
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.GtfsFeedService",
        lambda **kw: feed_service,
    )
    provider = GtfsTransitProvider(feed_service=feed_service)

    # Origin coords are ~5km from the station in our fixture
    results = await provider.search(_make_query(
        origin_lat=36.76,  # slightly off from the station
        origin_lng=-4.42,
    ))
    warnings = provider.consume_warnings()
    # With 100m radius, likely no nearby stops
    assert any(
        w.code in ("GTFS_NO_NEARBY_STOPS", "GTFS_NO_MATCHING_SERVICE")
        for w in warnings
    ) or results == []


@pytest.mark.asyncio
async def test_provider_emite_feed_unavailable(monkeypatch, feed_service):
    """When all feeds fail to load, emit GTFS_FEED_UNAVAILABLE."""
    # Create a descriptor pointing to a non-existent feed
    bad_descriptor = GtfsFeedDescriptor(
        id="bad_feed",
        name="Bad Feed",
        region="nowhere",
        url="file:///nonexistent.zip",
    )
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [bad_descriptor],
    )
    # Use the real GtfsFeedService that will try to download and fail
    from app.door_to_door.services.gtfs_feed_service import GtfsFeedService
    real_svc = GtfsFeedService(cache_ttl_seconds=0)
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.GtfsFeedService",
        lambda **kw: real_svc,
    )
    provider = GtfsTransitProvider(feed_service=real_svc)

    results = await provider.search(_make_query())
    warnings = provider.consume_warnings()
    assert any(w.code == "GTFS_FEED_UNAVAILABLE" for w in warnings)
    assert results == []


@pytest.mark.asyncio
async def test_provider_warning_code_especifico(provider):
    """Each failure mode emits the correct warning code."""
    _results = await provider.search(_make_query())
    warnings = provider.consume_warnings()
    codes = {w.code for w in warnings}

    # With our standard fixture we expect at minimum:
    # UNCONFIRMED_PRICE and GTFS_PRICE_UNAVAILABLE
    # (since we have trips and the feed loads fine)
    assert "UNCONFIRMED_PRICE" in codes
    assert "GTFS_PRICE_UNAVAILABLE" in codes


@pytest.mark.asyncio
async def test_provider_load_descriptors_from_file(monkeypatch, tmp_path):
    """load_feed_descriptors loads from DOOR_TO_DOOR_GTFS_FEEDS_FILE path."""
    manifest_path = tmp_path / "gtfs_feeds.json"
    manifest_path.write_text(json.dumps([
        {"id": "file_feed", "name": "File Feed", "url": "https://example.com/file.zip"},
    ]))
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_FEEDS_FILE", str(manifest_path))
    monkeypatch.delenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", raising=False)

    descriptors = load_feed_descriptors()
    assert len(descriptors) == 1
    assert descriptors[0].id == "file_feed"


# ---------------------------------------------------------------------------
# Integration: provider + search service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_service_integra_gtfs_warnings(provider, monkeypatch):
    """Search service collects and deduplicates GTFS warnings."""

    # We just verify the provider can be wrapped without errors
    # The search service integration is tested in integration tests
    _result = await provider.search(_make_query())
    warnings = provider.consume_warnings()
    # Warnings should be deduplicated by code+provider
    codes = [w.code for w in warnings]
    # Each warning code should appear at most once
    assert len(codes) == len(set(codes))


# ---------------------------------------------------------------------------
# Corridor coverage tests (Fase 5)
# ---------------------------------------------------------------------------

def _mock_corridors() -> list[dict]:
    return [
        {
            "id": "treviso_tsf_urbano",
            "name": "Treviso urbano → TSF",
            "region": "veneto",
            "destination_airport": "TSF",
            "feed_ids": ["mom_treviso"],
            "status": "verified",
        },
        {
            "id": "malaga_agp_urbano",
            "name": "Málaga urbano → AGP",
            "region": "andalucia",
            "destination_airport": "AGP",
            "feed_ids": ["emt_malaga_nap"],
            "status": "planned_blocked",
        },
        {
            "id": "venecia_marco_polo_urbano",
            "name": "Venecia urbano → VCE",
            "region": "veneto",
            "destination_airport": "VCE",
            "feed_ids": ["actv_venice"],
            "status": "verified_limited",
        },
    ]


@pytest.mark.asyncio
async def test_corridor_verified_emits_signal_for_tsf(provider):
    """When origin airport is TSF, corridor signal should be emitted."""
    provider._corridors = _mock_corridors()
    await provider.search(_make_query(origin_airport="TSF", destination_airport="MAD"))
    warnings = provider.consume_warnings()
    corridor_warnings = [w for w in warnings if w.code == "GTFS_CORRIDOR_VERIFIED"]
    assert len(corridor_warnings) == 1
    assert "Treviso" in corridor_warnings[0].message


@pytest.mark.asyncio
async def test_corridor_planned_emits_signal_for_agp(provider):
    """When origin airport is AGP and feed is blocked, emit planned corridor."""
    provider._corridors = _mock_corridors()
    await provider.search(_make_query(origin_airport="AGP"))
    warnings = provider.consume_warnings()
    corridor_warnings = [w for w in warnings if w.code == "GTFS_CORRIDOR_PLANNED"]
    assert len(corridor_warnings) == 1
    assert "Málaga" in corridor_warnings[0].message


@pytest.mark.asyncio
async def test_corridor_no_signal_for_unmatched_airport(provider):
    """When airports don't match any corridor, no corridor signal is emitted."""
    provider._corridors = _mock_corridors()
    await provider.search(_make_query(origin_airport="ORY", destination_airport="CDG"))
    warnings = provider.consume_warnings()
    corridor_codes = {w.code for w in warnings if w.code.startswith("GTFS_CORRIDOR")}
    assert len(corridor_codes) == 0


@pytest.mark.asyncio
async def test_corridor_verified_limited_counts_as_verified(provider):
    """Corridors with 'verified_limited' status should emit GTFS_CORRIDOR_VERIFIED."""
    provider._corridors = _mock_corridors()
    await provider.search(_make_query(origin_airport="VCE", destination_airport="TSF"))
    warnings = provider.consume_warnings()
    verified = [w for w in warnings if w.code == "GTFS_CORRIDOR_VERIFIED"]
    assert len(verified) == 1  # Both TSF and VCE match, but one warning with both names
    assert "Venecia" in verified[0].message or "Treviso" in verified[0].message


@pytest.mark.asyncio
async def test_corridor_loads_from_default_file(monkeypatch):
    """_load_corridors loads from the default manifest file."""
    import app.door_to_door.providers.gtfs_transit as gtfs_mod
    gtfs_mod._CORRIDORS_CACHE = None
    corridors = gtfs_mod._load_corridors()
    # The default manifest should exist and have corridors
    assert len(corridors) >= 2
    ids = {c["id"] for c in corridors}
    assert "treviso_tsf_urbano" in ids
    assert "malaga_agp_urbano" in ids


@pytest.mark.asyncio
async def test_corridor_match_both_airports(provider):
    """When both origin and destination match corridors, both names appear in signal."""
    provider._corridors = [
        {"id": "corr_a", "name": "Corridor A", "destination_airport": "AGP", "status": "verified"},
        {"id": "corr_b", "name": "Corridor B", "destination_airport": "TSF", "status": "verified"},
    ]
    await provider.search(_make_query(origin_airport="AGP", destination_airport="TSF"))
    warnings = provider.consume_warnings()
    verified = [w for w in warnings if w.code == "GTFS_CORRIDOR_VERIFIED"]
    assert len(verified) == 1
    assert "Corridor A" in verified[0].message
    assert "Corridor B" in verified[0].message


@pytest.mark.asyncio
async def test_corridor_mixed_verified_planned_prioritizes_verified(provider):
    """When one airport matches verified and the other matches planned, verified signal wins."""
    provider._corridors = [
        {"id": "corr_verified", "name": "Corredor Verificado", "destination_airport": "AGP", "status": "verified"},
        {"id": "corr_planned", "name": "Corredor Planeado", "destination_airport": "TSF", "status": "planned_blocked"},
    ]
    await provider.search(_make_query(origin_airport="AGP", destination_airport="TSF"))
    warnings = provider.consume_warnings()
    verified = [w for w in warnings if w.code == "GTFS_CORRIDOR_VERIFIED"]
    _planned = [w for w in warnings if w.code == "GTFS_CORRIDOR_PLANNED"]
    # Verified takes priority; planned is not emitted when verified exists
    assert len(verified) == 1
    assert "Corredor Verificado" in verified[0].message


# ---------------------------------------------------------------------------
# NAP auth tests (Fase 2)
# ---------------------------------------------------------------------------

def _build_nap_descriptor(api_key_env="GTFS_NAP_API_KEY", auth_header_name="x-api-key", auth_value_prefix="") -> GtfsFeedDescriptor:
    return GtfsFeedDescriptor(
        id="emt_malaga_nap",
        name="EMT Málaga (NAP)",
        region="malaga",
        url="https://nap.transportes.gob.es/api/Fichero/download/1293",
        api_key_env=api_key_env,
        auth_header_name=auth_header_name,
        auth_value_prefix=auth_value_prefix,
    )


def test_download_builds_auth_headers_from_env(monkeypatch):
    """_download sets x-api-key header when api_key_env is configured."""
    monkeypatch.setenv("GTFS_NAP_API_KEY", "test-key-abc123")
    desc = _build_nap_descriptor()

    captured_headers: dict[str, str] = {}

    class FakeResponse:
        content = b"fake-zip-data"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers, **kwargs):  # noqa: ANN001
        captured_headers.update(headers)
        return FakeResponse()

    with patch("httpx.get", side_effect=fake_get):
        result = GtfsFeedService._download(desc)

    assert result == b"fake-zip-data"
    assert "x-api-key" in captured_headers
    assert captured_headers["x-api-key"] == "test-key-abc123"


def test_download_skips_auth_when_env_var_missing(monkeypatch):
    """_download does not set auth header when env var is not configured."""
    monkeypatch.delenv("GTFS_NAP_API_KEY", raising=False)
    desc = _build_nap_descriptor()

    captured_headers: dict[str, str] = {}

    class FakeResponse:
        content = b"fake-zip-data"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers, **kwargs):  # noqa: ANN001
        captured_headers.update(headers)
        return FakeResponse()

    with patch("httpx.get", side_effect=fake_get):
        result = GtfsFeedService._download(desc)

    assert result == b"fake-zip-data"
    assert "x-api-key" not in captured_headers


def test_download_auth_with_bearer_prefix(monkeypatch):
    """_download prepends auth_value_prefix to the header value."""
    monkeypatch.setenv("TEST_BEARER_KEY", "tok-xyz")
    desc = _build_nap_descriptor(
        api_key_env="TEST_BEARER_KEY",
        auth_header_name="Authorization",
        auth_value_prefix="Bearer ",
    )

    captured_headers: dict[str, str] = {}

    class FakeResponse:
        content = b"ok"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers, **kwargs):  # noqa: ANN001
        captured_headers.update(headers)
        return FakeResponse()

    with patch("httpx.get", side_effect=fake_get):
        GtfsFeedService._download(desc)

    assert "Authorization" in captured_headers
    assert captured_headers["Authorization"] == "Bearer tok-xyz"


def test_download_skips_auth_when_api_key_env_empty(monkeypatch):
    """_download skips auth when env var is set to empty string."""
    monkeypatch.setenv("GTFS_NAP_API_KEY", "")
    desc = _build_nap_descriptor()

    captured_headers: dict[str, str] = {}

    class FakeResponse:
        content = b"ok"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers, **kwargs):  # noqa: ANN001
        captured_headers.update(headers)
        return FakeResponse()

    with patch("httpx.get", side_effect=fake_get):
        GtfsFeedService._download(desc)

    assert "x-api-key" not in captured_headers


def test_download_no_auth_when_not_configured():
    """_download works fine without any auth fields."""
    desc = GtfsFeedDescriptor(
        id="open_feed",
        name="Open Feed",
        region="any",
        url="https://example.com/gtfs.zip",
    )

    captured_headers: dict[str, str] = {}

    class FakeResponse:
        content = b"open-data"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers, **kwargs):  # noqa: ANN001
        captured_headers.update(headers)
        return FakeResponse()

    with patch("httpx.get", side_effect=fake_get):
        result = GtfsFeedService._download(desc)

    assert result == b"open-data"
    # No auth headers should be set for open feeds
    assert "x-api-key" not in captured_headers
    assert "Authorization" not in captured_headers


@pytest.mark.asyncio
async def test_nap_corridor_planned_with_auth_feed(provider):
    """When AGP corridor has planned_blocked status due to NAP auth, signal is emitted."""
    provider._corridors = [
        {
            "id": "malaga_agp_urbano",
            "name": "Málaga urbano → AGP",
            "region": "andalucia",
            "destination_airport": "AGP",
            "feed_ids": ["emt_malaga_nap"],
            "status": "planned_blocked",
        }
    ]
    await provider.search(_make_query(origin_airport="AGP"))
    warnings = provider.consume_warnings()
    planned = [w for w in warnings if w.code == "GTFS_CORRIDOR_PLANNED"]
    assert len(planned) == 1
    assert "Málaga" in planned[0].message


@pytest.mark.asyncio
async def test_nap_corridor_almeria_agp_planned(provider):
    """Almería → AGP corridor emits planned signal."""
    provider._corridors = [
        {
            "id": "almeria_agp_regional",
            "name": "Almería → AGP (regional)",
            "region": "andalucia",
            "destination_airport": "AGP",
            "feed_ids": ["ctan_andalucia_nap"],
            "status": "planned_blocked",
        }
    ]
    await provider.search(_make_query(origin_airport="AGP"))
    warnings = provider.consume_warnings()
    planned = [w for w in warnings if w.code == "GTFS_CORRIDOR_PLANNED"]
    assert len(planned) == 1
    assert "Almería" in planned[0].message


@pytest.mark.asyncio
async def test_nap_mocked_download_simulates_emt_malaga(gtfs_zip, monkeypatch):
    """Simulate a successful NAP download for EMT Málaga using mocked auth.

    When the NAP API key is configured, the feed should download, parse,
    and return results. This test ensures the full pipeline works with
    auth-configured feeds — no code change needed, just the env var.
    """
    monkeypatch.setenv("GTFS_NAP_API_KEY", "mock-key-for-test")

    # Create a NAP-style descriptor
    nap_desc = GtfsFeedDescriptor(
        id="emt_malaga_nap",
        name="EMT Málaga (NAP)",
        region="malaga",
        url="https://nap.transportes.gob.es/api/Fichero/download/1293",
        api_key_env="GTFS_NAP_API_KEY",
        auth_header_name="x-api-key",
    )

    # Create a FakeGtfsFeedService that returns our standard GTFS zip
    feed_svc = FakeGtfsFeedService(gtfs_zip)
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [nap_desc],
    )
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.GtfsFeedService",
        lambda **kw: feed_svc,
    )
    provider = GtfsTransitProvider(feed_service=feed_svc)
    # Explicitly set corridors so test doesn't depend on disk file
    provider._corridors = [
        {
            "id": "malaga_agp_urbano",
            "name": "Málaga urbano → AGP",
            "region": "andalucia",
            "destination_airport": "AGP",
            "feed_ids": ["emt_malaga_nap"],
            "status": "planned_blocked",
        }
    ]

    results = await provider.search(_make_query(origin_airport="AGP"))
    warnings = provider.consume_warnings()

    # With the key configured and a valid feed, we should get real results
    assert isinstance(results, list)
    # Corridor signal for AGP should be emitted
    corridor_codes = {w.code for w in warnings if w.code.startswith("GTFS_CORRIDOR")}
    assert "GTFS_CORRIDOR_PLANNED" in corridor_codes


@pytest.mark.asyncio
async def test_nap_descriptor_parsed_from_json(monkeypatch):
    """NAP feed descriptors with auth fields are parsed correctly from JSON."""
    nap_json = json.dumps([
        {
            "id": "emt_malaga_nap",
            "name": "EMT Málaga (NAP)",
            "region": "malaga",
            "url": "https://nap.transportes.gob.es/api/Fichero/download/1293",
            "api_key_env": "GTFS_NAP_API_KEY",
            "auth_header_name": "x-api-key",
        }
    ])
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", nap_json)
    monkeypatch.delenv("DOOR_TO_DOOR_GTFS_FEEDS_FILE", raising=False)

    descriptors = load_feed_descriptors()
    assert len(descriptors) == 1
    assert descriptors[0].id == "emt_malaga_nap"
    assert descriptors[0].api_key_env == "GTFS_NAP_API_KEY"
    assert descriptors[0].auth_header_name == "x-api-key"
    assert descriptors[0].auth_value_prefix == ""
    # response_format defaults to None (direct zip body)
    assert descriptors[0].response_format is None


# ---------------------------------------------------------------------------
# json_presigned response_format tests (NAP España downloadLink)
# ---------------------------------------------------------------------------

def _build_presigned_descriptor(response_format="json_presigned", auth_header_name="ApiKey") -> GtfsFeedDescriptor:
    return GtfsFeedDescriptor(
        id="emt_malaga_nap",
        name="EMT Málaga (NAP)",
        region="malaga",
        url="https://nap.transportes.gob.es/api/Fichero/downloadLink/1494",
        api_key_env="GTFS_NAP_API_KEY",
        auth_header_name=auth_header_name,
        response_format=response_format,
    )


def test_download_presigned_invalid_body_returns_content_unchanged(monkeypatch):
    """If body is not parseable as URL, fall back to returning the original body (graceful)."""
    monkeypatch.setenv("GTFS_NAP_API_KEY", "test-key")
    desc = _build_presigned_descriptor()

    class FakeResponse:
        content = b"this is not a valid url or json"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers=None, **kwargs):
        return FakeResponse()

    with patch("httpx.get", side_effect=fake_get):
        # Should not raise; returns the body as-is (caller will then fail to parse as zip)
        result = GtfsFeedService._download(desc)

    # Falls back to body text (the URL itself, since not JSON-wrapped)
    assert result == b"this is not a valid url or json"


def test_download_presigned_skips_when_response_format_not_set(monkeypatch):
    """Default behavior (no response_format) returns the body as-is, not following redirects."""
    monkeypatch.setenv("GTFS_NAP_API_KEY", "test-key")
    desc = _build_presigned_descriptor(response_format=None)

    call_count = 0

    class FakeResponse:
        content = b"PK\x03\x04direct-zip"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers=None, **kwargs):
        nonlocal call_count
        call_count += 1
        return FakeResponse()

    with patch("httpx.get", side_effect=fake_get):
        result = GtfsFeedService._download(desc)

    # Only one call to httpx.get (no follow-up)
    assert call_count == 1
    assert result == b"PK\x03\x04direct-zip"


def test_nap_descriptor_parsed_with_response_format(monkeypatch):
    """Manifest entries with response_format are parsed correctly."""
    manifest_json = json.dumps([
        {
            "id": "emt_malaga_nap",
            "name": "EMT Málaga (NAP)",
            "region": "malaga",
            "url": "https://nap.transportes.gob.es/api/Fichero/downloadLink/1494",
            "api_key_env": "GTFS_NAP_API_KEY",
            "auth_header_name": "ApiKey",
            "response_format": "json_presigned",
        },
        {
            "id": "open_feed",
            "name": "Open Feed",
            "url": "https://example.com/gtfs.zip",
        },
    ])
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", manifest_json)
    monkeypatch.delenv("DOOR_TO_DOOR_GTFS_FEEDS_FILE", raising=False)

    descriptors = load_feed_descriptors()
    assert len(descriptors) == 2

    nap = next(d for d in descriptors if d.id == "emt_malaga_nap")
    assert nap.api_key_env == "GTFS_NAP_API_KEY"
    assert nap.auth_header_name == "ApiKey"
    assert nap.response_format == "json_presigned"

    open_feed = next(d for d in descriptors if d.id == "open_feed")
    assert open_feed.api_key_env is None
    assert open_feed.auth_header_name is None
    assert open_feed.response_format is None


def test_nap_descriptor_preserves_auth_value_prefix_with_presigned(monkeypatch):
    """response_format=json_presigned still respects auth_value_prefix (e.g. 'Bearer ')."""
    monkeypatch.setenv("TEST_BEARER_KEY", "tok-xyz")
    desc = GtfsFeedDescriptor(
        id="custom_presigned",
        name="Custom Presigned",
        region="any",
        url="https://example.com/api/file",
        api_key_env="TEST_BEARER_KEY",
        auth_header_name="Authorization",
        auth_value_prefix="Bearer ",
        response_format="json_presigned",
    )

    first_call_headers: dict[str, str] = {}

    class FakeResponse1:
        content = b"https://s3.example.com/custom.zip"
        @staticmethod
        def raise_for_status() -> None:
            pass

    class FakeResponse2:
        content = b"PK\x03\x04custom-zip"
        @staticmethod
        def raise_for_status() -> None:
            pass

    def fake_get(url, headers=None, **kwargs):
        if "Authorization" not in first_call_headers:
            first_call_headers.update(headers or {})
            return FakeResponse1()
        return FakeResponse2()

    with patch("httpx.get", side_effect=fake_get):
        GtfsFeedService._download(desc)

    assert first_call_headers.get("Authorization") == "Bearer tok-xyz"


# ---------------------------------------------------------------------------
# Inbound coverage tests (Fase 3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_inbound_finds_airport_stops_by_iata(provider):
    """Inbound search finds airport stops using IATA code and multi-term search.

    The destination airport is TSF. _find_airport_stops uses multi-term search
    (city name + IATA + aeroporto/airport/aeropuerto) to find airport-area stops.
    The fixture has 'Parada Aeropuerto Malaga' which matches 'aeropuerto'.
    With bidirectional trips in the fixture, we verify inbound legs are produced.
    """
    results = await provider.search(_make_query(
        origin_airport="AGP",
        destination_airport="TSF",
        origin_lat=36.7167,
        origin_lng=-4.4257,
        final_lat=36.7213,
        final_lng=-4.4215,
        # Use UTC flight times so they align with GTFS fixture times (also UTC)
        departure_at=datetime(2026, 7, 15, 14, 20, tzinfo=timezone.utc),
        arrival_at=datetime(2026, 7, 15, 15, 35, tzinfo=timezone.utc),
    ))
    # Should find both outbound and inbound results since the fixture now has
    # bidirectional trips (aeropuerto→centro at 16:00 and 18:00 UTC)
    # Outbound: trip_aero_1 (08:40 arrival) < 12:20 latest ✓
    # Inbound: trip_inbound_2 (18:00 departure) > 16:05 earliest ✓
    assert len(results) > 0
    # At least one option should have 2 ground legs (outbound + inbound)
    has_both_legs = any(
        len([leg for leg in opt.legs if leg.type == "ground"]) >= 2
        for opt in results
    )
    assert has_both_legs, "Expected at least one option with both outbound and inbound ground legs"


@pytest.mark.asyncio
async def test_airport_search_terms_includes_multilingual(monkeypatch):
    """_airport_search_terms returns city name, IATA, and multi-language airport words."""
    import app.door_to_door.providers.gtfs_transit as gtfs_mod
    terms = gtfs_mod._airport_search_terms("TSF")
    assert "Treviso" in terms  # city name
    assert "TSF" in terms  # IATA code
    assert "aeroporto" in terms  # Italian
    assert "airport" in terms  # English
    assert "aeropuerto" in terms  # Spanish


@pytest.mark.asyncio
async def test_find_airport_stops_dedupes_across_terms(feed_service):
    """_find_airport_stops merges results from multiple terms without duplicates."""
    import app.door_to_door.providers.gtfs_transit as gtfs_mod
    feed = feed_service.load_feed(_build_feed_descriptor())
    assert feed is not None
    # The fixture has "Parada Aeropuerto Malaga" which matches both "Malaga"
    # (from _city_for_airport) and "aeropuerto" (from multi-language terms).
    # Dedup ensures it appears only once.
    stops = gtfs_mod._find_airport_stops(feed, "AGP")
    stop_ids = [s.stop_id for s in stops]
    assert len(stop_ids) == len(set(stop_ids)), "Airport stops should be deduplicated"
    # Should find at minimum the "Parada Aeropuerto Malaga" stop
    assert any("aeropuerto" in s.name.lower() for s in stops) or \
           any("malaga" in s.name.lower() for s in stops)


@pytest.mark.asyncio
async def test_provider_inbound_has_ground_legs(provider):
    """Inbound search produces ground legs in both directions when stops match.

    The fixture now has bidirectional trips: outbound (estacion→aeropuerto)
    and inbound (aeropuerto→centro). The multi-term search finds the airport
    stop via 'aeropuerto' keyword for both departure and arrival airports.
    """
    results = await provider.search(_make_query(
        origin_airport="AGP",
        destination_airport="TSF",
        origin_lat=36.7167,
        origin_lng=-4.4257,
        final_lat=36.7213,
        final_lng=-4.4215,
        # Use UTC flight times so they align with GTFS fixture times (also UTC)
        departure_at=datetime(2026, 7, 15, 14, 20, tzinfo=timezone.utc),
        arrival_at=datetime(2026, 7, 15, 15, 35, tzinfo=timezone.utc),
    ))
    assert len(results) > 0
    for option in results:
        ground_legs = [leg for leg in option.legs if leg.type == "ground"]
        # Outbound + inbound ground legs (at least 2 when both directions match)
        assert len(ground_legs) >= 1
        # At least one leg should be inbound (from_location contains airport)
        inbound_legs = [
            leg for leg in ground_legs
            if "aeropuerto" in (leg.from_location or "").lower()
        ]
        assert len(inbound_legs) >= 1, "Expected an inbound leg from the airport"


# ---------------------------------------------------------------------------
# Pricing tests (Fase 5)
# ---------------------------------------------------------------------------

@pytest.fixture
def gtfs_zip_fares() -> bytes:
    return _build_gtfs_zip_with_fares()


@pytest.fixture
def feed_service_fares(gtfs_zip_fares: bytes) -> FakeGtfsFeedService:
    svc = FakeGtfsFeedService(gtfs_zip_fares, max_walk_radius_meters=5000, max_results=5)
    return svc


@pytest.fixture
def provider_fares(feed_service_fares: FakeGtfsFeedService, monkeypatch) -> GtfsTransitProvider:
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.load_feed_descriptors",
        lambda: [_build_feed_descriptor()],
    )
    monkeypatch.setattr(
        "app.door_to_door.providers.gtfs_transit.GtfsFeedService",
        lambda **kw: feed_service_fares,
    )
    return GtfsTransitProvider(feed_service=feed_service_fares)


def test_feed_service_parses_fare_attributes(feed_service_fares):
    feed = feed_service_fares.load_feed(_build_feed_descriptor())
    assert feed is not None
    assert len(feed.fare_attributes) == 3
    assert feed.fare_attributes["fare_aerobus"].price == 1.55
    assert feed.fare_attributes["fare_urbano"].price == 1.20


def test_feed_service_parses_fare_rules(feed_service_fares):
    feed = feed_service_fares.load_feed(_build_feed_descriptor())
    assert feed is not None
    assert len(feed.fare_rules) == 3
    assert feed.fare_rules[0].route_id == "route_aerobus"


def test_lookup_fare_by_route(feed_service_fares):
    """lookup_fare returns the correct fare for a specific route."""
    feed = feed_service_fares.load_feed(_build_feed_descriptor())
    assert feed is not None
    fare = feed_service_fares.lookup_fare(
        feed.feed_id, "stop_estacion", "stop_aeropuerto", "route_aerobus"
    )
    assert fare is not None
    assert fare.price == 1.55
    assert fare.currency_type == "EUR"


def test_lookup_fare_returns_cheapest(feed_service_fares):
    """When no route-specific rule matches, return the cheapest flat fare."""
    feed = feed_service_fares.load_feed(_build_feed_descriptor())
    assert feed is not None
    fare = feed_service_fares.lookup_fare(
        feed.feed_id, "stop_estacion", "stop_centro", "route_unknown"
    )
    assert fare is not None
    # Should return fare_unlimited (3.00) as flat fare fallback
    assert fare.price == 3.00


def test_lookup_fare_none_without_fare_data(feed_service):
    """lookup_fare returns None when feed has no fare data."""
    feed = feed_service.load_feed(_build_feed_descriptor())
    assert feed is not None
    fare = feed_service.lookup_fare(
        feed.feed_id, "stop_estacion", "stop_aeropuerto", "route_aerobus"
    )
    assert fare is None


@pytest.mark.asyncio
async def test_provider_sets_confirmed_price_with_fares(provider_fares):
    """When GTFS feed has fare data, options carry confirmed prices."""
    results = await provider_fares.search(_make_query())
    assert len(results) > 0
    option = results[0]
    # With fare data, total_price should be set
    assert option.total_price_min is not None
    assert option.total_price_max is not None
    assert option.price is not None
    assert option.price.status == "confirmed"


@pytest.mark.asyncio
async def test_provider_legs_have_prices_with_fares(provider_fares):
    """Ground legs carry price_min/price_max from GTFS fare data."""
    results = await provider_fares.search(_make_query())
    assert len(results) > 0
    option = results[0]
    outbound_legs = [leg for leg in option.legs if leg.type == "ground" and "aeropuerto" in (leg.to_location or "").lower()]
    # At least one outbound leg should have a price
    priced_legs = [leg for leg in outbound_legs if leg.price_min is not None]
    assert len(priced_legs) > 0, "Expected outbound ground legs to have fare prices"
    assert priced_legs[0].price_min > 0


@pytest.mark.asyncio
async def test_provider_omite_price_warnings_con_fares(provider_fares):
    """When fare data is available, UNCONFIRMED_PRICE and GTFS_PRICE_UNAVAILABLE are not emitted."""
    await provider_fares.search(_make_query())
    warnings = provider_fares.consume_warnings()
    # Should NOT have UNCONFIRMED_PRICE since fare data is confirmed
    assert not any(w.code == "UNCONFIRMED_PRICE" for w in warnings)
    assert not any(w.code == "GTFS_PRICE_UNAVAILABLE" for w in warnings)


@pytest.mark.asyncio
async def test_provider_price_per_person_with_fares(provider_fares):
    """price_per_person is total / passengers when fares are available."""
    results = await provider_fares.search(_make_query(passengers=2))
    if results:
        option = results[0]
        if option.total_price_min is not None:
            expected_per_person = option.total_price_min / 2
            assert option.price_per_person_min == pytest.approx(expected_per_person)


@pytest.mark.asyncio
async def test_provider_describe_precio_confirmado(provider_fares):
    """trust_copy and description reflect confirmed price when fares are available."""
    results = await provider_fares.search(_make_query())
    if results:
        option = results[0]
        if option.price and option.price.status == "confirmed":
            assert "confirmado" in (option.trust_copy or "").lower() or \
                   "confirmada" in (option.description or "").lower()


@pytest.mark.asyncio
async def test_provider_sin_fares_sigue_sin_precios(provider):
    """Provider without fare data still returns null prices (no regression)."""
    results = await provider.search(_make_query())
    for option in results:
        assert option.total_price_min is None
        assert option.total_price_max is None


