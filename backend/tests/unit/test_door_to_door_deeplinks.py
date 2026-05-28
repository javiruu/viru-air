"""Unit tests for BlaBlaCar and GoOpti deeplink providers."""

from datetime import datetime, timedelta, timezone

import pytest

from app.door_to_door.providers.deeplink_blablacar import BlaBlaCarDeepLinkProvider
from app.door_to_door.providers.deeplink_goopti import GoOptiDeepLinkProvider
from app.door_to_door.providers.base import DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorLocation,
    DoorToDoorPreferences,
)


def _make_query(
    *,
    origin_label="Almería",
    origin_type="city",
    final_type="city",
    final_label="Treviso centro",
    allow_rideshare=True,
    allow_shuttle=True,
    public_transport_only=False,
    min_airport_buffer_minutes=120,
    max_price=None,
    passengers=1,
    origin_airport="AGP",
    destination_airport="TSF",
    flight_time_confidence="estimated",
    departure_at=None,
    arrival_at=None,
) -> DoorToDoorProviderQuery:
    now = datetime.now(tz=timezone.utc)
    dep = departure_at or (now + timedelta(days=14))
    arr = arrival_at or (dep + timedelta(hours=2, minutes=35))

    return DoorToDoorProviderQuery(
        origin=DoorToDoorLocation(type=origin_type, label=origin_label),
        final_destination=DoorToDoorLocation(type=final_type, label=final_label),
        preferences=DoorToDoorPreferences(
            min_airport_buffer_minutes=min_airport_buffer_minutes,
            max_price=max_price,
            passengers=passengers,
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


# ---------------------------------------------------------------------------
# BlaBlaCarDeepLinkProvider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_blablacar_generates_booking_url_with_origin_dest_date():
    provider = BlaBlaCarDeepLinkProvider()
    query = _make_query()
    results = await provider.search(query)
    assert len(results) == 1
    option = results[0]
    assert option.id == "option_blablacar_deeplink"
    assert option.total_price_min is None
    assert option.total_price_max is None
    assert option.confidence == "deeplink"
    assert option.source_types == ["deeplink", "api"]
    assert option.legs[0].mode == "rideshare"

    blablacar_source = next(s for s in option.sources if s.provider == "blablacar_deeplink")
    booking_url = blablacar_source.booking_url
    assert booking_url is not None
    assert booking_url.startswith("https://www.blablacar.es/search?")
    assert "fn=Almer%C3%ADa" in booking_url
    assert "tn=M%C3%A1laga" in booking_url or "tn=Malaga" in booking_url
    assert query.flight.departure_at.date().isoformat() in booking_url


@pytest.mark.asyncio
async def test_blablacar_no_inventa_precio():
    provider = BlaBlaCarDeepLinkProvider()
    results = await provider.search(_make_query())
    option = results[0]
    assert option.total_price_min is None
    assert option.total_price_max is None
    assert option.price_per_person_min is None
    assert option.price_per_person_max is None
    for leg in option.legs:
        assert leg.price_min is None
        assert leg.price_max is None


@pytest.mark.asyncio
async def test_blablacar_provider_generates_raw_option_even_if_allow_rideshare_false():
    provider = BlaBlaCarDeepLinkProvider()
    results = await provider.search(_make_query(allow_rideshare=False))
    assert len(results) == 1
    assert results[0].id == "option_blablacar_deeplink"


@pytest.mark.asyncio
async def test_blablacar_provider_generates_raw_option_even_if_public_transport_only():
    provider = BlaBlaCarDeepLinkProvider()
    results = await provider.search(_make_query(
        public_transport_only=True,
        allow_rideshare=False,  # schemas normalizer sets this automatically
    ))
    assert len(results) == 1
    assert results[0].id == "option_blablacar_deeplink"


@pytest.mark.asyncio
async def test_blablacar_emite_warning_unconfirmed_price():
    provider = BlaBlaCarDeepLinkProvider()
    await provider.search(_make_query())
    warnings = provider.consume_warnings()
    assert any(w.code == "UNCONFIRMED_PRICE" for w in warnings)


@pytest.mark.asyncio
async def test_blablacar_emite_flight_time_estimated_warning():
    provider = BlaBlaCarDeepLinkProvider()
    await provider.search(_make_query(flight_time_confidence="estimated"))
    warnings = provider.consume_warnings()
    assert any(w.code == "FLIGHT_TIME_ESTIMATED" for w in warnings)


@pytest.mark.asyncio
async def test_blablacar_usa_fecha_del_vuelo():
    provider = BlaBlaCarDeepLinkProvider()
    departure = datetime(2026, 8, 15, 14, 20, tzinfo=timezone(timedelta(hours=2)))
    query = _make_query(departure_at=departure)
    results = await provider.search(query)
    blablacar_source = next(s for s in results[0].sources if s.provider == "blablacar_deeplink")
    assert "2026-08-15" in (blablacar_source.booking_url or "")


@pytest.mark.asyncio
async def test_blablacar_diferentes_aeropuertos():
    """BlaBlaCar debe funcionar para otros aeropuertos además de AGP."""
    provider = BlaBlaCarDeepLinkProvider()
    departure = datetime(2026, 9, 1, 8, 0, tzinfo=timezone(timedelta(hours=2)))
    arrival = departure + timedelta(hours=2)
    query = _make_query(
        origin_label="Barcelona",
        origin_airport="BCN",
        destination_airport="FCO",
        departure_at=departure,
        arrival_at=arrival,
    )
    results = await provider.search(query)
    assert len(results) == 1
    blablacar_source = next(s for s in results[0].sources if s.provider == "blablacar_deeplink")
    assert "Barcelona" in (blablacar_source.booking_url or "")


@pytest.mark.asyncio
async def test_blablacar_aeropuerto_desconocido_emite_warning_parcial():
    """Cuando el IATA del aeropuerto no esta en el mapping de ciudades, el deeplink es parcial."""
    provider = BlaBlaCarDeepLinkProvider()
    query = _make_query(origin_label="Almeria", origin_airport="XXX")
    await provider.search(query)
    warnings = provider.consume_warnings()
    # El deeplink deberia funcionar (tiene origen y fecha) pero el destino
    # Aeropuerto de XXX no se mapea a ciudad conocida -> BLABLACAR_DEEPLINK_PARTIAL
    assert any(w.code == "BLABLACAR_DEEPLINK_PARTIAL" for w in warnings)


@pytest.mark.asyncio
async def test_blablacar_max_price_no_filtra_deeplink_sin_precio():
    provider = BlaBlaCarDeepLinkProvider()
    results = await provider.search(_make_query(max_price=20))
    assert len(results) == 1
    assert results[0].total_price_min is None


# ---------------------------------------------------------------------------
# GoOptiDeepLinkProvider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_goopti_generates_booking_url_con_aeropuerto_destino_fecha():
    provider = GoOptiDeepLinkProvider()
    query = _make_query()
    results = await provider.search(query)
    assert len(results) == 1
    option = results[0]
    assert option.id == "option_goopti_deeplink"
    assert option.total_price_min is None
    assert option.total_price_max is None
    assert option.confidence == "deeplink"
    assert option.legs[2].mode == "shuttle"
    assert option.legs[2].provider == "goopti"

    goopti_source = next(s for s in option.sources if s.provider == "goopti_deeplink")
    booking_url = goopti_source.booking_url
    assert booking_url is not None
    assert booking_url.startswith("https://www.goopti.com/es/?")
    assert "pickup=Aeropuerto+de+TSF" in booking_url
    assert "dropoff=Treviso+centro" in booking_url


@pytest.mark.asyncio
async def test_goopti_no_inventa_precio():
    provider = GoOptiDeepLinkProvider()
    results = await provider.search(_make_query())
    option = results[0]
    assert option.total_price_min is None
    assert option.total_price_max is None
    assert option.price_per_person_min is None
    assert option.price_per_person_max is None
    for leg in option.legs:
        assert leg.price_min is None
        assert leg.price_max is None


@pytest.mark.asyncio
async def test_goopti_respeta_allow_shuttle_false():
    provider = GoOptiDeepLinkProvider()
    results = await provider.search(_make_query(allow_shuttle=False))
    assert results == []


@pytest.mark.asyncio
async def test_goopti_no_se_muestra_si_airport_only():
    provider = GoOptiDeepLinkProvider()
    results = await provider.search(_make_query(final_type="airport_only", final_label="Solo aeropuerto TSF"))
    assert results == []


@pytest.mark.asyncio
async def test_goopti_emite_warning_unconfirmed_price():
    provider = GoOptiDeepLinkProvider()
    await provider.search(_make_query())
    warnings = provider.consume_warnings()
    assert any(w.code == "UNCONFIRMED_PRICE" for w in warnings)


@pytest.mark.asyncio
async def test_goopti_emite_flight_time_estimated_warning():
    provider = GoOptiDeepLinkProvider()
    await provider.search(_make_query(flight_time_confidence="estimated"))
    warnings = provider.consume_warnings()
    assert any(w.code == "FLIGHT_TIME_ESTIMATED" for w in warnings)


@pytest.mark.asyncio
async def test_goopti_usa_fecha_llegada_del_vuelo():
    provider = GoOptiDeepLinkProvider()
    departure = datetime(2026, 8, 15, 14, 20, tzinfo=timezone(timedelta(hours=2)))
    arrival = departure + timedelta(hours=2, minutes=35)
    query = _make_query(departure_at=departure, arrival_at=arrival)
    results = await provider.search(query)
    goopti_source = next(s for s in results[0].sources if s.provider == "goopti_deeplink")
    assert "2026-08-15" in (goopti_source.booking_url or "")


@pytest.mark.asyncio
async def test_goopti_aeropuerto_desconocido_no_bloquea_deeplink():
    """GoOpti usa el IATA directamente en pickup, no necesita mapping de ciudad."""
    provider = GoOptiDeepLinkProvider()
    query = _make_query(
        final_label="Venecia centro",
        destination_airport="VCE",
    )
    results = await provider.search(query)
    assert len(results) == 1
    goopti_source = next(s for s in results[0].sources if s.provider == "goopti_deeplink")
    assert "Aeropuerto+de+VCE" in (goopti_source.booking_url or "")


@pytest.mark.asyncio
async def test_goopti_max_price_no_filtra_deeplink_sin_precio():
    provider = GoOptiDeepLinkProvider()
    results = await provider.search(_make_query(max_price=20))
    assert len(results) == 1
    assert results[0].total_price_min is None


# ---------------------------------------------------------------------------
# Provider status
# ---------------------------------------------------------------------------

def test_provider_status_clasifica_ambos_como_functional_deeplink():
    from app.door_to_door.providers.registry import (
        BlaBlaCarDeepLinkProvider,
        GoOptiDeepLinkProvider,
        ProviderDescriptor,
        resolve_provider_runtime,
    )
    import os

    # Set env for the test
    os.environ["APP_ENV"] = "test"
    os.environ["DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER"] = "0"
    os.environ["DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS"] = "1"
    os.environ["DOOR_TO_DOOR_ENABLE_SCRAPERS"] = "0"
    os.environ.pop("GOOGLE_MAPS_API_KEY", None)

    runtime = resolve_provider_runtime()
    statuses = {s.name: s for s in runtime.statuses}

    assert statuses["blablacar_deeplink"].enabled is True
    assert statuses["blablacar_deeplink"].status == "functional_deeplink"
    assert statuses["blablacar_deeplink"].source_type == "deeplink"
    assert statuses["blablacar_deeplink"].supports_search is True
    assert statuses["blablacar_deeplink"].supports_booking_url is True
    assert statuses["blablacar_deeplink"].has_tests is True

    assert statuses["goopti_deeplink"].enabled is True
    assert statuses["goopti_deeplink"].status == "functional_deeplink"
    assert statuses["goopti_deeplink"].source_type == "deeplink"
    assert statuses["goopti_deeplink"].supports_search is True
    assert statuses["goopti_deeplink"].supports_booking_url is True
    assert statuses["goopti_deeplink"].has_tests is True
