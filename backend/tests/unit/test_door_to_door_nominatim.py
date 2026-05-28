from __future__ import annotations

import asyncio

from app.door_to_door.providers.nominatim import NominatimSuggestionsProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = ""

    def json(self) -> object:
        return self._payload


def test_nominatim_disabled_returns_empty(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NOMINATIM_SUGGESTIONS", "0")
    provider = NominatimSuggestionsProvider()
    items = asyncio.run(provider.suggest("madrid", limit=4))
    assert items == []


def test_nominatim_normalizes_items_with_open_data_source(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NOMINATIM_SUGGESTIONS", "1")

    def fake_get(*args, **kwargs):  # noqa: ANN002,ANN003
        return _FakeResponse(
            200,
            [
                {
                    "place_id": "12345",
                    "display_name": "Madrid, Comunidad de Madrid, España",
                    "lat": "40.4167",
                    "lon": "-3.7033",
                    "class": "place",
                    "type": "city",
                    "address": {"city": "Madrid", "country": "España"},
                }
            ],
        )

    monkeypatch.setattr("app.door_to_door.providers.nominatim.requests.get", fake_get)

    provider = NominatimSuggestionsProvider()
    items = asyncio.run(provider.suggest("madrid", limit=4))
    assert len(items) == 1
    assert items[0].source_type == "open_data"
    assert items[0].type == "city"
    assert items[0].lat == 40.4167
    assert items[0].lng == -3.7033


def test_nominatim_applies_soft_region_preference(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NOMINATIM_SUGGESTIONS", "1")

    def fake_get(*args, **kwargs):  # noqa: ANN002,ANN003
        return _FakeResponse(
            200,
            [
                {
                    "place_id": "us_1",
                    "display_name": "Springfield, Illinois, United States",
                    "class": "place",
                    "type": "city",
                    "address": {"city": "Springfield", "country": "United States"},
                },
                {
                    "place_id": "es_1",
                    "display_name": "Springfield, Madrid, España",
                    "class": "place",
                    "type": "city",
                    "address": {"city": "Springfield", "country": "España"},
                },
            ],
        )

    monkeypatch.setattr("app.door_to_door.providers.nominatim.requests.get", fake_get)
    provider = NominatimSuggestionsProvider()
    items = asyncio.run(provider.suggest("springfield", limit=4, preferred_region_codes=["es"]))
    assert len(items) == 2
    assert "España" in items[0].subtitle
    assert "United States" in items[1].subtitle


def test_nominatim_handles_http_error(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_NOMINATIM_SUGGESTIONS", "1")

    def fake_get(*args, **kwargs):  # noqa: ANN002,ANN003
        return _FakeResponse(500, [])

    monkeypatch.setattr("app.door_to_door.providers.nominatim.requests.get", fake_get)
    provider = NominatimSuggestionsProvider()
    items = asyncio.run(provider.suggest("lisboa", limit=4))
    assert items == []
