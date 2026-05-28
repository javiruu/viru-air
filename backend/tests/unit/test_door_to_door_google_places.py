from __future__ import annotations

import asyncio

from app.door_to_door.providers.google_places import GooglePlacesSuggestionsProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_google_places_disabled_without_key(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    provider = GooglePlacesSuggestionsProvider()
    suggestions = asyncio.run(provider.suggest("alme", limit=4))

    assert suggestions == []
    health = asyncio.run(provider.healthcheck())
    assert health.status == "missing_api_key"


def test_google_places_suggestions_are_normalized_with_api_source(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")

    call_counter = {"count": 0}

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        call_counter["count"] += 1
        return _FakeResponse(
            200,
            {
                "suggestions": [
                    {
                        "placePrediction": {
                            "placeId": "place_almeria",
                            "text": {"text": "Almería"},
                            "structuredFormat": {
                                "secondaryText": {"text": "Andalucía, España"}
                            },
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("app.door_to_door.providers.google_places.requests.post", fake_post)

    provider = GooglePlacesSuggestionsProvider()
    items = asyncio.run(provider.suggest("alme", limit=4))

    assert len(items) == 1
    assert items[0].source_type == "api"
    assert items[0].label == "Almería"
    assert items[0].place_id == "place_almeria"
    assert call_counter["count"] == 1


def test_google_places_suggestions_use_cache(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")

    call_counter = {"count": 0}

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        call_counter["count"] += 1
        return _FakeResponse(
            200,
            {
                "suggestions": [
                    {
                        "placePrediction": {
                            "placeId": "place_treviso",
                            "text": {"text": "Treviso"},
                            "structuredFormat": {
                                "secondaryText": {"text": "Veneto, Italia"}
                            },
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("app.door_to_door.providers.google_places.requests.post", fake_post)

    provider = GooglePlacesSuggestionsProvider()
    first = asyncio.run(provider.suggest("trevi", limit=4))
    second = asyncio.run(provider.suggest("trevi", limit=4))

    assert first
    assert second
    assert call_counter["count"] == 1


def test_google_places_suggestions_include_session_token_when_provided(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")

    captured_body: dict[str, object] = {}

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        body = kwargs.get("json") or {}
        captured_body.update(body)
        return _FakeResponse(200, {"suggestions": []})

    monkeypatch.setattr("app.door_to_door.providers.google_places.requests.post", fake_post)

    provider = GooglePlacesSuggestionsProvider()
    asyncio.run(provider.suggest("alme", limit=4, session_token="session-123"))

    assert captured_body.get("sessionToken") == "session-123"


def test_google_places_supports_query_prediction_shape(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        return _FakeResponse(
            200,
            {
                "suggestions": [
                    {
                        "queryPrediction": {
                            "text": {"text": "Avenida Pablo Iglesias, Madrid"},
                            "structuredFormat": {
                                "secondaryText": {"text": "Madrid, España"}
                            },
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("app.door_to_door.providers.google_places.requests.post", fake_post)

    provider = GooglePlacesSuggestionsProvider()
    items = asyncio.run(provider.suggest("avenida pablo iglesias", limit=4))

    assert len(items) == 1
    assert "Avenida Pablo Iglesias" in items[0].label
    assert items[0].source_type == "api"


def test_google_places_cache_key_changes_with_session_token(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")

    call_counter = {"count": 0}

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        call_counter["count"] += 1
        return _FakeResponse(
            200,
            {
                "suggestions": [
                    {
                        "placePrediction": {
                            "placeId": "place_treviso",
                            "text": {"text": "Treviso"},
                            "structuredFormat": {
                                "secondaryText": {"text": "Veneto, Italia"}
                            },
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("app.door_to_door.providers.google_places.requests.post", fake_post)

    provider = GooglePlacesSuggestionsProvider()
    first = asyncio.run(provider.suggest("trevi", limit=4, session_token="session-a"))
    second = asyncio.run(provider.suggest("trevi", limit=4, session_token="session-b"))

    assert first
    assert second
    assert call_counter["count"] == 2


def test_google_places_cache_prunes_entries_with_max_limit(monkeypatch) -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-google-key")
    monkeypatch.setenv("DOOR_TO_DOOR_GOOGLE_PLACES_CACHE_MAX_ENTRIES", "50")

    def fake_post(*args, **kwargs):  # noqa: ANN002,ANN003
        query = (kwargs.get("json") or {}).get("input", "unknown")
        return _FakeResponse(
            200,
            {
                "suggestions": [
                    {
                        "placePrediction": {
                            "placeId": f"place_{query}",
                            "text": {"text": str(query)},
                            "structuredFormat": {
                                "secondaryText": {"text": "Test region"}
                            },
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("app.door_to_door.providers.google_places.requests.post", fake_post)

    provider = GooglePlacesSuggestionsProvider()
    for idx in range(60):
        asyncio.run(provider.suggest(f"query-{idx}", limit=4))

    assert len(provider._cache) <= provider.max_cache_entries
