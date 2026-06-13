"""
Unit tests: verify that DeeplinkDoorToDoorProvider generates correct actions.

Fase 2: actions must use airport city names, coordinates when available,
and BlaBlaCar place_ids when resolvable.

Run with:  python -m pytest tests/test_deeplink_actions.py -v
"""
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.door_to_door.providers.deeplink_provider import DeeplinkDoorToDoorProvider
from app.door_to_door.providers.base import DoorToDoorProviderQuery
from app.door_to_door.schemas import (
    DoorToDoorFlightOut,
    DoorToDoorLocation,
    DoorToDoorPreferences,
)

MADRID = ZoneInfo("Europe/Madrid")


def _make_query(*, airport_only=False, allow_rideshare=True, allow_shuttle=True, origin_coords=True, origin_place_id=None):
    now = datetime.now(tz=MADRID)
    departure = now + timedelta(hours=3)
    arrival = departure + timedelta(hours=2, minutes=35)
    flight = DoorToDoorFlightOut(
        origin_airport="AGP",
        destination_airport="TSF",
        departure_at=departure,
        arrival_at=arrival,
        flight_time_confidence="estimated",
    )
    origin = DoorToDoorLocation(
        type="city", label="Almeria",
        lat=36.834 if origin_coords else None,
        lng=-2.463 if origin_coords else None,
        place_id=origin_place_id,
    )
    final = (
        DoorToDoorLocation(type="airport_only", label="Solo aeropuerto TSF")
        if airport_only
        else DoorToDoorLocation(type="city", label="Treviso centro", lat=45.666, lng=12.245)
    )
    prefs = DoorToDoorPreferences(allow_rideshare=allow_rideshare, allow_shuttle=allow_shuttle)
    return DoorToDoorProviderQuery(
        origin=origin, final_destination=final, preferences=prefs, flight=flight, checked_at=now,
    )


@pytest.mark.asyncio
async def test_ground_legs_always_have_google_maps():
    """Every ground leg must have at least a Google Maps action."""
    provider = DeeplinkDoorToDoorProvider()
    options = await provider.search(_make_query())
    assert len(options) == 1
    option = options[0]
    assert option.status == "real_deeplink"
    assert len(option.legs) == 3  # ground, flight, ground

    for leg in option.legs:
        if leg.type != "ground":
            continue
        gm = [a for a in leg.actions if a.provider == "google_maps"]
        assert len(gm) == 1, f"Ground leg {leg.from_location}->{leg.to_location} missing Google Maps"
        action = gm[0]
        assert action.kind == "directions"
        assert action.price_status == "external"
        assert action.availability_status == "external"
        assert action.opens_external is True
        assert "google.com/maps" in action.url


@pytest.mark.asyncio
async def test_no_invented_data_on_ground_legs():
    """Ground legs must NOT invent price, duration, or schedule."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query()))[0]
    for leg in option.legs:
        if leg.type != "ground":
            continue
        assert leg.price_min is None
        assert leg.duration_minutes is None
        assert leg.departure_at is None


@pytest.mark.asyncio
async def test_airport_only_has_2_legs():
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query(airport_only=True)))[0]
    assert len(option.legs) == 2
    assert option.legs[0].type == "ground"
    assert option.legs[1].type == "flight"
    assert len(option.legs[0].actions) >= 1


@pytest.mark.asyncio
async def test_blablacar_depends_on_rideshare():
    provider = DeeplinkDoorToDoorProvider()

    with_rs = (await provider.search(_make_query(allow_rideshare=True)))[0]
    without_rs = (await provider.search(_make_query(allow_rideshare=False)))[0]

    bbc_with = [a for a in with_rs.legs[0].actions if a.provider == "blablacar"]
    bbc_without = [a for a in without_rs.legs[0].actions if a.provider == "blablacar"]
    assert len(bbc_with) == 1
    assert len(bbc_without) == 0


@pytest.mark.asyncio
async def test_goopti_depends_on_shuttle():
    provider = DeeplinkDoorToDoorProvider()

    with_sh = (await provider.search(_make_query(allow_shuttle=True)))[0]
    without_sh = (await provider.search(_make_query(allow_shuttle=False)))[0]

    go_with = [a for a in with_sh.legs[2].actions if a.provider == "goopti"]
    go_without = [a for a in without_sh.legs[2].actions if a.provider == "goopti"]
    assert len(go_with) == 1
    assert len(go_without) == 0


@pytest.mark.asyncio
async def test_json_serialization_preserves_actions():
    """Actions must survive model_dump(by_alias=True) — what FastAPI sends."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query()))[0]
    dumped = option.model_dump(mode="json", by_alias=True)
    for leg in dumped["legs"]:
        if leg["type"] != "ground":
            continue
        assert len(leg["actions"]) >= 1, f"Actions lost in JSON for {leg['from']}->{leg['to']}"
        for action in leg["actions"]:
            assert "id" in action
            assert "provider" in action
            assert "url" in action
            assert action["price_status"] == "external"
            assert action["availability_status"] == "external"
            assert action["opens_external"] is True


# ── Fase 2: airport city labels ──────────────────────────────────

@pytest.mark.asyncio
async def test_airport_labels_include_city_names():
    """Airport labels must use city names, not just IATA codes."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query()))[0]

    origin_leg = option.legs[0]
    assert "Málaga" in origin_leg.to_location
    assert "AGP" in origin_leg.to_location

    dest_leg = option.legs[2]
    assert "Treviso" in dest_leg.from_location
    assert "TSF" in dest_leg.from_location


@pytest.mark.asyncio
async def test_google_maps_action_uses_coordinates_when_available():
    """Google Maps URL must use lat,lng when coordinates are available."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query(origin_coords=True)))[0]

    gm_action = next(a for a in option.legs[0].actions if a.provider == "google_maps")
    assert gm_action is not None
    assert "36.834" in gm_action.url
    assert "-2.463" in gm_action.url


@pytest.mark.asyncio
async def test_google_maps_action_falls_back_to_labels_without_coordinates():
    """Google Maps URL must use text labels when coordinates are missing."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query(origin_coords=False)))[0]

    gm_action = next(a for a in option.legs[0].actions if a.provider == "google_maps")
    assert gm_action is not None
    # Should use quoted text labels, not lat,lng
    assert "google.com/maps/dir/?api=1" in gm_action.url
    assert "Almeria" in gm_action.url or "Almer%C3%ADa" in gm_action.url


@pytest.mark.asyncio
async def test_blablacar_action_resolves_place_id_for_known_airport():
    """BlaBlaCar deeplink must include place_id for airports with known mappings."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query(allow_rideshare=True)))[0]

    bbc_action = next(a for a in option.legs[0].actions if a.provider == "blablacar")
    assert bbc_action is not None
    # AGP is mapped to Málaga place_id
    assert "to_place_id" in bbc_action.url or "from_place_id" in bbc_action.url
    assert "eyJ" in bbc_action.url  # place_id token prefix


@pytest.mark.asyncio
async def test_blablacar_action_still_works_without_place_id():
    """BlaBlaCar deeplink must still generate a valid search URL without place_ids."""
    now = datetime.now(tz=MADRID)
    departure = now + timedelta(hours=3)
    arrival = departure + timedelta(hours=2, minutes=35)

    flight = DoorToDoorFlightOut(
        origin_airport="XXX",
        destination_airport="YYY",
        departure_at=departure,
        arrival_at=arrival,
        flight_time_confidence="estimated",
    )
    origin = DoorToDoorLocation(type="city", label="Almeria")
    final = DoorToDoorLocation(type="city", label="Treviso centro")
    prefs = DoorToDoorPreferences(allow_rideshare=True, allow_shuttle=True)
    query = DoorToDoorProviderQuery(
        origin=origin, final_destination=final, preferences=prefs, flight=flight, checked_at=now,
    )

    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(query))[0]

    bbc_action = next(a for a in option.legs[0].actions if a.provider == "blablacar")
    assert bbc_action is not None
    assert "blablacar.es/search" in bbc_action.url
    assert "fn=" in bbc_action.url
    assert "tn=" in bbc_action.url
    # URL is valid even without place_id — just uses text search


@pytest.mark.asyncio
async def test_goopti_action_uses_airport_city_label():
    """GoOpti deeplink must use airport city in pickup label."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query(allow_shuttle=True)))[0]

    go_action = next(a for a in option.legs[2].actions if a.provider == "goopti")
    assert go_action is not None
    assert "Treviso" in go_action.url
    assert "TSF" in go_action.url
    assert "dropoff=Treviso+centro" in go_action.url


@pytest.mark.asyncio
async def test_option_description_mentions_all_three_providers():
    """The actionable option description must name the providers it covers."""
    provider = DeeplinkDoorToDoorProvider()
    option = (await provider.search(_make_query()))[0]

    assert "Google Maps" in option.description
    assert "BlaBlaCar" in option.description
    assert "GoOpti" in option.description



