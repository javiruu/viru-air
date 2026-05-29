"""
Unit tests: verify that DeeplinkDoorToDoorProvider generates correct actions.

Run with:  python -m pytest tests/test_deeplink_actions.py -v
"""
import pytest
import asyncio
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


def _make_query(*, airport_only=False, allow_rideshare=True, allow_shuttle=True):
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
    origin = DoorToDoorLocation(type="city", label="Almeria", lat=36.834, lng=-2.463)
    final = (
        DoorToDoorLocation(type="airport_only", label="Solo aeropuerto TSF")
        if airport_only
        else DoorToDoorLocation(type="city", label="Treviso centro")
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
