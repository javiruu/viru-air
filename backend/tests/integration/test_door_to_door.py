from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorOptionOut
from app.door_to_door.services.search_service import DoorToDoorSearchService
from tests.helpers import register_and_token


def _set_provider_env(
    monkeypatch,
    *,
    mock: bool,
    real: bool,
    scrapers: bool = False,
    google_routes: bool = False,
    google_places: bool = False,
    google_key: str | None = None,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER", "1" if mock else "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS", "1" if real else "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_SCRAPERS", "1" if scrapers else "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES", "1" if google_routes else "0")
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES", "1" if google_places else "0")
    if google_key is None:
        monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", google_key)


def _auth_headers(client: TestClient, email: str = "door@viru.dev") -> dict[str, str]:
    token = register_and_token(client, email=email, password="Pass1234")
    return {"Authorization": f"Bearer {token}"}


def _create_watch(client: TestClient, headers: dict[str, str]) -> str:
    payload = {
        "origin_iata": "AGP",
        "destination_iata": "TSF",
        "travel_date_local": str(date.today() + timedelta(days=30)),
        "target_price": 60,
    }
    response = client.post("/api/v1/watchlist", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _search_payload(watch_id: str) -> dict:
    return {
        "flight_watch_id": watch_id,
        "origin": {"type": "city", "label": "Almería", "lat": 36.834, "lng": -2.463},
        "final_destination": {"type": "city", "label": "Treviso centro"},
        "preferences": {
            "min_airport_buffer_minutes": 120,
            "max_price": 80,
            "passengers": 1,
            "luggage": "cabin",
            "allow_bus": True,
            "allow_train": True,
            "allow_rideshare": True,
            "allow_shuttle": True,
            "allow_taxi": False,
            "allow_car": True,
            "public_transport_only": False,
            "sort_by": "best_balance",
        },
    }


def test_mock_active_returns_mock_options_with_warning(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client)
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["options"]
    assert any(warning["code"] == "ESTIMATED_MOCK_DATA" for warning in body["warnings"])
    assert all(option["confidence"] == "estimated" for option in body["options"])
    assert all(option["source_types"] == ["mock"] for option in body["options"])


def test_mock_disabled_without_real_returns_no_coverage(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=False, scrapers=False)
    headers = _auth_headers(client, "no-real@viru.dev")
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["options"] == []
    assert any(warning["code"] == "NO_REAL_PROVIDER_COVERAGE" for warning in body["warnings"])
    assert any(warning["code"] == "NO_COVERAGE" for warning in body["warnings"])


def test_deeplink_provider_returns_booking_url_without_price(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    headers = _auth_headers(client, "deeplink@viru.dev")
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    deeplink_options = [option for option in body["options"] if "deeplink" in option["source_types"]]
    assert deeplink_options
    assert all(option["total_price_min"] is None and option["total_price_max"] is None for option in deeplink_options)
    assert any(
        (source.get("booking_url") or "").startswith("https://")
        for option in deeplink_options
        for source in option["sources"]
        if source["source_type"] == "deeplink"
    )


def test_provider_status_classifies_stubs_and_runtime_flags(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    headers = _auth_headers(client, "status@viru.dev")

    response = client.get("/api/v1/door-to-door/providers/status", headers=headers)

    assert response.status_code == 200, response.text
    statuses = {item["name"]: item for item in response.json()}
    assert statuses["blablacar_deeplink"]["enabled"] is True
    assert statuses["blablacar_deeplink"]["status"] == "functional_deeplink"
    assert statuses["mock_multimodal"]["enabled"] is False
    assert statuses["mock_multimodal"]["status"] == "disabled"
    assert statuses["google_routes"]["status"] == "disabled"
    assert statuses["google_routes"]["supports_search"] is False
    assert statuses["blablacar_scraper"]["status"] == "scraper_base_only"
    assert statuses["blablacar_scraper"]["enabled"] is False


def test_provider_status_marks_google_routes_functional_when_flag_and_key(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        scrapers=False,
        google_routes=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "status-google@viru.dev")

    response = client.get("/api/v1/door-to-door/providers/status", headers=headers)

    assert response.status_code == 200, response.text
    statuses = {item["name"]: item for item in response.json()}
    assert statuses["google_routes"]["enabled"] is True
    assert statuses["google_routes"]["status"] == "functional_api"
    assert statuses["google_routes"]["supports_search"] is True


def test_provider_status_marks_google_routes_disabled_without_key(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        scrapers=False,
        google_routes=True,
        google_key=None,
    )
    headers = _auth_headers(client, "status-google-nokey@viru.dev")

    response = client.get("/api/v1/door-to-door/providers/status", headers=headers)

    assert response.status_code == 200, response.text
    statuses = {item["name"]: item for item in response.json()}
    assert statuses["google_routes"]["enabled"] is False
    assert statuses["google_routes"]["status"] == "disabled"
    assert "GOOGLE_MAPS_API_KEY" in (statuses["google_routes"]["notes"] or "")


def test_watchid_alias_and_estimated_flight_warning(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client, "watchid@viru.dev")
    watch_id = _create_watch(client, headers)
    payload = _search_payload(watch_id)
    payload["watchId"] = payload.pop("flight_watch_id")

    response = client.post("/api/v1/door-to-door/search", json=payload, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["flight"]["origin_airport"] == "AGP"
    assert body["flight"]["flight_time_confidence"] == "estimated"
    assert any(warning["code"] == "FLIGHT_TIME_ESTIMATED" for warning in body["warnings"])


def test_airport_only_omits_arrival_ground_leg(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client, "airport-only@viru.dev")
    watch_id = _create_watch(client, headers)
    payload = _search_payload(watch_id)
    payload["final_destination"] = {"type": "airport_only", "label": "Solo aeropuerto TSF"}

    response = client.post("/api/v1/door-to-door/search", json=payload, headers=headers)

    assert response.status_code == 200, response.text
    legs = response.json()["options"][0]["legs"]
    assert [leg["type"] for leg in legs] == ["ground", "flight"]
    assert legs[-1]["to"] == "TSF"


def test_source_metadata_is_present(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client, "source@viru.dev")
    watch_id = _create_watch(client, headers)

    body = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers).json()
    source = body["options"][0]["sources"][0]

    assert source["provider"]
    assert source["source_provider"]
    assert source["source_type"] == "mock"
    assert source["confidence"] == "estimated"
    assert source["checked_at"]
    assert source["expires_at"]


def test_provider_failure_does_not_break_search(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    from app.door_to_door.api import routes

    class FailingProvider(DoorToDoorProvider):
        provider_name = "failing_provider"
        source_type = "api"

        async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
            raise RuntimeError("provider down")

        async def healthcheck(self):  # pragma: no cover
            raise RuntimeError("provider down")

    class MixedService(DoorToDoorSearchService):
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
            from app.door_to_door.providers.mock import MockDoorToDoorProvider

            super().__init__([FailingProvider(), MockDoorToDoorProvider()])

    monkeypatch.setattr(routes, "DoorToDoorSearchService", MixedService)
    headers = _auth_headers(client, "partial@viru.dev")
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["options"]
    assert any(warning["code"] == "PARTIAL_PROVIDER_COVERAGE" for warning in body["warnings"])
    assert any(warning["code"] == "PROVIDER_PARTIAL_COVERAGE" for warning in body["warnings"])


def test_search_returns_api_option_when_google_routes_provider_is_simulated(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_routes=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-routes-search@viru.dev")
    watch_id = _create_watch(client, headers)

    from app.door_to_door.providers import deeplink_blablacar, deeplink_goopti, google_routes
    from app.door_to_door.schemas import DoorToDoorLegOut, DoorToDoorOptionOut, DoorToDoorSourceOut

    async def _empty_search(self, query):  # noqa: ANN001
        return []

    async def _fake_google_search(self, query):  # noqa: ANN001
        checked_at = query.checked_at
        return [
            DoorToDoorOptionOut(
                id="option_google_routes_test",
                label="Duración real de ruta terrestre",
                description="Duración y distancia calculadas con proveedor de rutas.",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=505,
                risk_level="medium",
                score=72,
                transfer_count=2,
                airport_buffer_minutes=130,
                confidence="live",
                source_types=["api"],
                sources=[
                    DoorToDoorSourceOut(
                        provider="google_routes",
                        source_provider="google_routes",
                        source_type="api",
                        confidence="live",
                        checked_at=checked_at,
                    )
                ],
                legs=[
                    DoorToDoorLegOut(
                        type="ground",
                        mode="car",
                        from_label="Almería",
                        to_label="Aeropuerto de Málaga AGP",
                        duration_minutes=215,
                        distance_meters=198000,
                        provider="google_routes",
                        source_type="api",
                        confidence="live",
                    ),
                    DoorToDoorLegOut(
                        type="flight",
                        mode="flight",
                        from_label="AGP",
                        to_label="TSF",
                        duration_minutes=155,
                        provider="flight_watch",
                        source_type="api",
                        confidence="estimated",
                    ),
                ],
            )
        ]

    monkeypatch.setattr(deeplink_blablacar.BlaBlaCarDeepLinkProvider, "search", _empty_search)
    monkeypatch.setattr(deeplink_goopti.GoOptiDeepLinkProvider, "search", _empty_search)
    monkeypatch.setattr(google_routes.GoogleRoutesProvider, "search", _fake_google_search)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    api_options = [option for option in body["options"] if option["source_types"] == ["api"]]
    assert api_options
    assert api_options[0]["total_price_min"] is None
    assert api_options[0]["legs"][0]["distance_meters"] == 198000


def test_suggestions_merge_local_static_and_google_places(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_places=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-places-suggestions@viru.dev")
    from app.door_to_door.providers import google_places
    from app.door_to_door.schemas import DoorToDoorSuggestionOut

    async def _fake_suggest(self, query, *, limit=6):  # noqa: ANN001
        return [
            DoorToDoorSuggestionOut(
                id="google_treviso",
                type="city",
                label="Treviso",
                subtitle="Google Places",
                source_type="api",
                place_id="place_treviso",
            )
        ]

    monkeypatch.setattr(google_places.GooglePlacesSuggestionsProvider, "suggest", _fake_suggest)
    response = client.get("/api/v1/door-to-door/suggestions?q=tre", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()
    assert any(item["source_type"] == "api" for item in items)
    assert any(item["source_type"] == "local_static" for item in items)


def test_suggestions_keep_local_static_when_google_places_disabled(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, google_places=False, google_key=None)
    headers = _auth_headers(client, "google-places-off@viru.dev")

    response = client.get("/api/v1/door-to-door/suggestions?q=tre", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()
    assert items
    assert all(item["source_type"] == "local_static" for item in items)


def test_score_prefers_safer_route_when_buffer_is_low() -> None:
    safe = score_itinerary(55, 520, 150, 2, "low", "estimated")
    risky = score_itinerary(30, 420, 65, 1, "high", "estimated")
    assert safe > risky


def test_high_risk_when_airport_buffer_under_90() -> None:
    assert calculate_risk_level(89, 1, "estimated") == "high"
