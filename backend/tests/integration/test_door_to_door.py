from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.infrastructure.db.models import DoorToDoorSearchHistory, PriceSnapshot
from app.infrastructure.db.session import get_db
from app.main import app
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


def _create_watch(client: TestClient, headers: dict[str, str], *, origin_iata: str = "AGP", destination_iata: str = "TSF") -> str:
    payload = {
        "origin_iata": origin_iata,
        "destination_iata": destination_iata,
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


def _open_test_db_session():
    override = app.dependency_overrides[get_db]
    db_gen = override()
    db = next(db_gen)
    return db, db_gen


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
    assert all(option["source_types"] == ["estimate"] for option in body["options"])


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
    deeplink_source = next(
        source
        for option in deeplink_options
        for source in option["sources"]
        if source["source_type"] == "deeplink" and source["provider"] == "blablacar_deeplink"
    )
    assert (deeplink_source.get("booking_url") or "").startswith("https://www.blablacar.es/search?")
    parsed = urlparse(deeplink_source["booking_url"])
    params = parse_qs(parsed.query)
    assert params.get("fn")
    assert params.get("tn")
    assert params.get("db")
    assert params.get("seats") == ["1"]
    assert params.get("search_origin") == ["SEARCH"]
    assert params.get("p0[ac]") == ["adult"]
    assert params.get("from_place_id")
    assert params.get("to_place_id")
    assert "from" not in params
    assert "to" not in params
    assert "date" not in params


def test_blablacar_deeplink_fallback_without_place_id_keeps_valid_url(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    headers = _auth_headers(client, "deeplink-fallback@viru.dev")
    watch_id = _create_watch(client, headers)
    payload = _search_payload(watch_id)
    payload["origin"] = {"type": "city", "label": "Pueblo sin token", "lat": None, "lng": None, "place_id": None}

    response = client.post("/api/v1/door-to-door/search", json=payload, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    deeplink_options = [option for option in body["options"] if option["id"] == "option_blablacar_deeplink"]
    assert deeplink_options
    deeplink_source = next(
        source for source in deeplink_options[0]["sources"] if source["provider"] == "blablacar_deeplink"
    )
    parsed = urlparse(deeplink_source["booking_url"])
    params = parse_qs(parsed.query)
    assert params.get("fn") == ["Pueblo sin token, España"]
    assert params.get("tn")
    assert params.get("db")
    assert not params.get("from_place_id")
    assert any(warning["code"] == "BLABLACAR_DEEPLINK_PARTIAL" for warning in body["warnings"])


def test_blablacar_is_hidden_when_rideshare_is_disabled(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    headers = _auth_headers(client, "deeplink-rideshare-off@viru.dev")
    watch_id = _create_watch(client, headers)
    payload = _search_payload(watch_id)
    payload["preferences"]["allow_rideshare"] = False

    response = client.post("/api/v1/door-to-door/search", json=payload, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert all(option["id"] != "option_blablacar_deeplink" for option in body["options"])


def test_blablacar_is_hidden_when_public_transport_only_is_enabled(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    headers = _auth_headers(client, "deeplink-public-only@viru.dev")
    watch_id = _create_watch(client, headers)
    payload = _search_payload(watch_id)
    payload["preferences"]["public_transport_only"] = True

    response = client.post("/api/v1/door-to-door/search", json=payload, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert all(option["id"] != "option_blablacar_deeplink" for option in body["options"])


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


def test_flight_time_warning_not_emitted_when_departure_time_is_available(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client, "watchid-live-time@viru.dev")
    watch_id = _create_watch(client, headers)
    payload = _search_payload(watch_id)

    db, db_gen = _open_test_db_session()
    try:
        db.add(
            PriceSnapshot(
                watch_id=watch_id,
                departure_time_local="09:45",
                raw_price=49.99,
                raw_currency="EUR",
                provider="test-provider",
            )
        )
        db.commit()
    finally:
        db_gen.close()

    response = client.post("/api/v1/door-to-door/search", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["flight"]["flight_time_confidence"] == "live"
    assert not any(warning["code"] == "FLIGHT_TIME_ESTIMATED" for warning in body["warnings"])


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
    assert source["source_type"] == "estimate"
    assert source["confidence"] == "estimated"
    assert source["checked_at"]
    assert "expires_at" in source


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
                        from_location="Almería",
                        to_location="Aeropuerto de Málaga AGP",
                        duration_minutes=215,
                        distance_meters=198000,
                        provider="google_routes",
                        source_type="api",
                        confidence="live",
                    ),
                    DoorToDoorLegOut(
                        type="flight",
                        mode="flight",
                        from_location="AGP",
                        to_location="TSF",
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


def test_deeplink_options_are_enriched_with_google_routes_metrics(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_routes=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-routes-deeplink@viru.dev")
    watch_id = _create_watch(client, headers)

    from app.door_to_door.providers import google_routes
    from app.door_to_door.schemas import DoorToDoorLegOut, DoorToDoorOptionOut, DoorToDoorSourceOut

    async def _fake_google_search(self, query):  # noqa: ANN001
        checked_at = query.checked_at
        return [
            DoorToDoorOptionOut(
                id="option_google_routes_test_enrichment",
                label="Duración real de ruta terrestre",
                description="Duración y distancia calculadas con proveedor de rutas.",
                status="real_result",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=505,
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
                        from_location="Almería",
                        to_location="Aeropuerto de Málaga AGP",
                        departure_at="2026-06-14T08:00:00+02:00",
                        arrival_at="2026-06-14T11:00:00+02:00",
                        duration_minutes=180,
                        distance_meters=198000,
                        provider="google_routes",
                        source_type="api",
                        confidence="live",
                    ),
                    DoorToDoorLegOut(
                        type="flight",
                        mode="flight",
                        from_location="AGP",
                        to_location="TSF",
                        duration_minutes=155,
                        provider="flight_watch",
                        source_type="api",
                        confidence="estimated",
                    ),
                    DoorToDoorLegOut(
                        type="ground",
                        mode="car",
                        from_location="Treviso Airport TSF",
                        to_location="Treviso centro",
                        departure_at="2026-06-14T17:20:00+02:00",
                        arrival_at="2026-06-14T17:55:00+02:00",
                        duration_minutes=35,
                        distance_meters=6000,
                        provider="google_routes",
                        source_type="api",
                        confidence="live",
                    ),
                ],
            )
        ]

    monkeypatch.setattr(google_routes.GoogleRoutesProvider, "search", _fake_google_search)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    deeplink_options = [option for option in body["options"] if option["status"] == "real_deeplink"]
    assert deeplink_options
    for option in deeplink_options:
        assert option["total_duration_minutes"] is not None
        assert any(source["provider"] == "google_routes" for source in option["sources"])
        assert any(leg["type"] == "ground" and leg.get("distance_meters") is not None for leg in option["legs"])
        assert option.get("deep_link") and option["deep_link"].get("url")


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

    async def _fake_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
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
    payload = response.json()
    items = payload["items"]
    assert payload["meta"]["provider_status"] == "api_live"
    assert any(item["source_type"] == "api" for item in items)
    assert any(item["source_type"] == "local_static" for item in items)


def test_suggestions_keep_homonyms_with_different_place_id(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_places=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-places-homonyms@viru.dev")
    from app.door_to_door.providers import google_places
    from app.door_to_door.schemas import DoorToDoorSuggestionOut

    async def _fake_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
        return [
            DoorToDoorSuggestionOut(
                id="google_springfield_us",
                type="city",
                label="Springfield",
                subtitle="Illinois, US",
                source_type="api",
                place_id="place_springfield_us",
            ),
            DoorToDoorSuggestionOut(
                id="google_springfield_uk",
                type="city",
                label="Springfield",
                subtitle="Fife, UK",
                source_type="api",
                place_id="place_springfield_uk",
            ),
        ]

    monkeypatch.setattr(google_places.GooglePlacesSuggestionsProvider, "suggest", _fake_suggest)
    response = client.get("/api/v1/door-to-door/suggestions?q=spring", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    springfields = [item for item in payload["items"] if item["label"] == "Springfield" and item["source_type"] == "api"]
    assert len(springfields) == 2


def test_suggestions_send_origin_country_code_from_selected_watch(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_places=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-places-region-origin@viru.dev")
    watch_id = _create_watch(client, headers)
    captured: dict[str, object] = {}
    from app.door_to_door.providers import google_places

    async def _fake_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
        captured["preferred_region_codes"] = preferred_region_codes
        return []

    monkeypatch.setattr(google_places.GooglePlacesSuggestionsProvider, "suggest", _fake_suggest)
    response = client.get(f"/api/v1/door-to-door/suggestions?q=Madrid&field=origin&watch_id={watch_id}", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["meta"]["used_region_codes"] == ["es"]
    assert captured.get("preferred_region_codes") == ["es"]


def test_suggestions_send_destination_country_code_from_selected_watch(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_places=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-places-region-destination@viru.dev")
    watch_id = _create_watch(client, headers)
    captured: dict[str, object] = {}
    from app.door_to_door.providers import google_places

    async def _fake_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
        captured["preferred_region_codes"] = preferred_region_codes
        return []

    monkeypatch.setattr(google_places.GooglePlacesSuggestionsProvider, "suggest", _fake_suggest)
    response = client.get(f"/api/v1/door-to-door/suggestions?q=Luxembourg&field=destination&watch_id={watch_id}", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["meta"]["used_region_codes"] == ["it"]
    assert captured.get("preferred_region_codes") == ["it"]


def test_suggestions_keep_local_static_when_google_places_disabled(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, google_places=False, google_key=None)
    headers = _auth_headers(client, "google-places-off@viru.dev")

    response = client.get("/api/v1/door-to-door/suggestions?q=tre", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    items = payload["items"]
    assert payload["meta"]["provider_status"] == "fallback_active"
    assert items
    assert any(item["source_type"] == "open_data" for item in items)


def test_suggestions_include_typed_fallback_when_provider_is_disabled(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, google_places=False, google_key=None)
    headers = _auth_headers(client, "google-places-typed-disabled@viru.dev")
    query = "avenida pablo iglesias"

    response = client.get(f"/api/v1/door-to-door/suggestions?q={query}", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["meta"]["provider_status"] == "fallback_active"
    assert any(item["label"].lower() == query for item in payload["items"])
    assert any("fallback local" in item["subtitle"].lower() for item in payload["items"])


def test_suggestions_provider_error_returns_fallback_with_meta(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_places=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-places-provider-error@viru.dev")
    from app.door_to_door.providers import google_places

    async def _failing_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(google_places.GooglePlacesSuggestionsProvider, "suggest", _failing_suggest)
    response = client.get("/api/v1/door-to-door/suggestions?q=tre", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["meta"]["provider_status"] == "fallback_active"
    assert payload["meta"]["degraded_reason"] == "google_unavailable_using_open_data"
    assert payload["items"]
    assert any(item["source_type"] == "open_data" for item in payload["items"])


def test_suggestions_provider_error_still_includes_typed_fallback(client: TestClient, monkeypatch) -> None:
    _set_provider_env(
        monkeypatch,
        mock=False,
        real=True,
        google_places=True,
        google_key="fake-google-key",
    )
    headers = _auth_headers(client, "google-places-provider-error-typed@viru.dev")
    query = "avenida pablo iglesias"
    from app.door_to_door.providers import google_places

    async def _failing_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(google_places.GooglePlacesSuggestionsProvider, "suggest", _failing_suggest)
    response = client.get(f"/api/v1/door-to-door/suggestions?q={query}", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["meta"]["provider_status"] == "fallback_active"
    assert any(item["label"].lower() == query for item in payload["items"])


def test_suggestions_prioritize_exact_match_and_context_country_for_mad(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, google_places=False, google_key=None)
    headers = _auth_headers(client, "suggestions-context-mad@viru.dev")
    watch_id = _create_watch(client, headers, origin_iata="MAD", destination_iata="LUX")
    from app.door_to_door.providers import nominatim
    from app.door_to_door.schemas import DoorToDoorSuggestionOut

    async def _fake_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
        return [
            DoorToDoorSuggestionOut(
                id="almere",
                type="city",
                label="Almere",
                subtitle="Flevoland, Países Bajos",
                source_type="open_data",
                lat=52.3508,
                lng=5.2647,
                place_id="osm:almere",
            ),
            DoorToDoorSuggestionOut(
                id="almeria_es",
                type="city",
                label="Almería",
                subtitle="Andalucía, España",
                source_type="open_data",
                lat=36.834,
                lng=-2.463,
                place_id="osm:almeria",
            ),
        ]

    monkeypatch.setattr(nominatim.NominatimSuggestionsProvider, "suggest", _fake_suggest)
    response = client.get(f"/api/v1/door-to-door/suggestions?q=almeria&field=origin&watch_id={watch_id}", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["items"][0]["label"] == "Almería"
    assert "España" in payload["items"][0]["subtitle"]


def test_suggestions_deduplicate_same_city_with_multiple_place_ids(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, google_places=False, google_key=None)
    headers = _auth_headers(client, "suggestions-dedupe@viru.dev")
    from app.door_to_door.providers import nominatim
    from app.door_to_door.schemas import DoorToDoorSuggestionOut

    async def _fake_suggest(self, query, *, limit=6, session_token=None, preferred_region_codes=None):  # noqa: ANN001
        return [
            DoorToDoorSuggestionOut(
                id="almeria_a",
                type="city",
                label="Almería",
                subtitle="Andalucía, España",
                source_type="open_data",
                lat=36.8341,
                lng=-2.4637,
                place_id="osm:111",
            ),
            DoorToDoorSuggestionOut(
                id="almeria_b",
                type="city",
                label="Almeria",
                subtitle="Andalucía, España",
                source_type="open_data",
                lat=36.8340,
                lng=-2.4636,
                place_id="osm:222",
            ),
        ]

    monkeypatch.setattr(nominatim.NominatimSuggestionsProvider, "suggest", _fake_suggest)
    response = client.get("/api/v1/door-to-door/suggestions?q=almeria&field=origin", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    almeria_items = [
        item for item in payload["items"]
        if item["source_type"] == "open_data" and item["label"].lower().startswith("almer")
    ]
    assert len(almeria_items) == 1


def test_score_prefers_safer_route_when_buffer_is_low() -> None:
    high_buffer = score_itinerary(55, 420, 155, 2, "estimated")
    low_buffer = score_itinerary(55, 420, 90, 2, "estimated")
    assert high_buffer > low_buffer


def test_score_rewards_stronger_buffer() -> None:
    assert score_itinerary(60, 420, 155, 2, "estimated") > score_itinerary(60, 420, 100, 2, "estimated")


def _set_gtfs_env(monkeypatch, *, gtfs_enabled: bool, feeds_json: str = "") -> None:
    monkeypatch.setenv("DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT", "1" if gtfs_enabled else "0")
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_FEEDS_JSON", feeds_json)
    monkeypatch.setenv("DOOR_TO_DOOR_GTFS_CACHE_DIR", ".gtfs_cache_test")


def test_gtfs_disabled_yields_no_change(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    _set_gtfs_env(monkeypatch, gtfs_enabled=False, feeds_json="")
    headers = _auth_headers(client, "gtfs-off@viru.dev")
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert all("open_data" not in option["source_types"] for option in body["options"])


def test_gtfs_on_without_feeds_shows_disabled_status(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    _set_gtfs_env(monkeypatch, gtfs_enabled=True, feeds_json="")
    headers = _auth_headers(client, "gtfs-nofeed@viru.dev")

    response = client.get("/api/v1/door-to-door/providers/status", headers=headers)

    assert response.status_code == 200, response.text
    statuses = {item["name"]: item for item in response.json()}
    assert statuses["gtfs_transit"]["enabled"] is False
    assert statuses["gtfs_transit"]["status"] == "disabled"
    assert "faltan feeds" in (statuses["gtfs_transit"]["notes"] or "").lower() or "feeds" in (statuses["gtfs_transit"]["notes"] or "").lower()


def test_gtfs_provider_failure_does_not_break_search(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=True, scrapers=False)
    _set_gtfs_env(monkeypatch, gtfs_enabled=True, feeds_json='[{"id":"test_feed","name":"Test Feed","region":"test","url":"https://example.com/gtfs.zip","source_type":"open_data","license_url":"https://example.com/license","attribution":"Test"}]')

    from app.door_to_door.providers import gtfs_transit

    original_search = gtfs_transit.GtfsTransitProvider.search

    async def _failing_search(self, query):
        raise RuntimeError("GTFS feed unavailable")

    monkeypatch.setattr(gtfs_transit.GtfsTransitProvider, "search", _failing_search)

    headers = _auth_headers(client, "gtfs-fail@viru.dev")
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["options"]
    assert any(warning["code"] in ("PARTIAL_PROVIDER_COVERAGE", "PROVIDER_PARTIAL_COVERAGE", "GTFS_FEED_UNAVAILABLE") for warning in body["warnings"])

    monkeypatch.setattr(gtfs_transit.GtfsTransitProvider, "search", original_search)


def test_gtfs_with_mock_returns_open_data_option(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    _set_gtfs_env(monkeypatch, gtfs_enabled=True, feeds_json='[{"id":"test_feed","name":"Test Feed","region":"test","url":"https://example.com/gtfs.zip","source_type":"open_data","license_url":"https://example.com/license","attribution":"Test"}]')

    from app.door_to_door.providers import gtfs_transit
    from app.door_to_door.schemas import DoorToDoorLegOut, DoorToDoorOptionOut, DoorToDoorSourceOut

    async def _fake_gtfs_search(self, query):
        checked_at = query.checked_at
        return [
            DoorToDoorOptionOut(
                id="option_gtfs_test",
                label="Transporte público (horario real)",
                description="Horario según feed público GTFS.",
                total_price_min=None,
                total_price_max=None,
                price_per_person_min=None,
                price_per_person_max=None,
                currency="EUR",
                total_duration_minutes=320,
                score=68,
                transfer_count=1,
                airport_buffer_minutes=130,
                confidence="cached",
                source_types=["open_data"],
                sources=[
                    DoorToDoorSourceOut(
                        provider="gtfs_transit",
                        source_provider="ctan_andalucia",
                        source_type="open_data",
                        confidence="cached",
                        checked_at=checked_at,
                    )
                ],
                legs=[
                    DoorToDoorLegOut(
                        type="ground",
                        mode="bus",
                        from_location="Almería",
                        to_location="Aeropuerto de Málaga AGP",
                        departure_at="2026-06-14T07:30:00+02:00",
                        arrival_at="2026-06-14T11:00:00+02:00",
                        duration_minutes=210,
                        provider="gtfs_transit",
                        source_type="open_data",
                        confidence="cached",
                    ),
                    DoorToDoorLegOut(
                        type="flight",
                        mode="flight",
                        from_location="AGP",
                        to_location="TSF",
                        duration_minutes=155,
                        provider="flight_watch",
                        source_type="api",
                        confidence="estimated",
                    ),
                ],
            )
        ]

    monkeypatch.setattr(gtfs_transit.GtfsTransitProvider, "search", _fake_gtfs_search)

    headers = _auth_headers(client, "gtfs-mock@viru.dev")
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    open_data_options = [option for option in body["options"] if "open_data" in option["source_types"]]
    assert open_data_options
    assert open_data_options[0]["total_price_min"] is None
    assert open_data_options[0]["total_price_max"] is None
    assert any(source["source_type"] == "open_data" for source in open_data_options[0]["sources"])


def test_gtfs_provider_status_is_honest(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=False, real=True, scrapers=False)
    _set_gtfs_env(monkeypatch, gtfs_enabled=True, feeds_json='[{"id":"test_feed","name":"Test","region":"test","url":"https://example.com/gtfs.zip","source_type":"open_data","license_url":"https://example.com/license","attribution":"Test"}]')
    headers = _auth_headers(client, "gtfs-status@viru.dev")

    response = client.get("/api/v1/door-to-door/providers/status", headers=headers)

    assert response.status_code == 200, response.text
    statuses = {item["name"]: item for item in response.json()}
    assert statuses["gtfs_transit"]["enabled"] is True
    assert statuses["gtfs_transit"]["status"] == "functional_open_data"
    assert statuses["gtfs_transit"]["source_type"] == "open_data"
    assert statuses["gtfs_transit"]["supports_search"] is True
    assert statuses["gtfs_transit"]["supports_booking_url"] is False
    assert statuses["gtfs_transit"]["has_tests"] is True
    assert statuses["gtfs_transit"]["production_ready"] is False


def test_history_returns_last_chosen_option_for_same_history_id(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client, "history-last-chosen@viru.dev")
    watch_id = _create_watch(client, headers)

    search_response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)
    assert search_response.status_code == 200, search_response.text
    search_body = search_response.json()
    history_id = search_body["summary"]["history_id"]
    assert history_id
    first = {"id": "option_first", "label": "First choice"}
    second = {"id": "option_second", "label": "Second choice"}

    choose_first = client.post(
        f"/api/v1/door-to-door/history/{history_id}/chosen",
        json={"option_id": first["id"], "option_label": first["label"], "option_summary": {}},
        headers=headers,
    )
    assert choose_first.status_code == 200, choose_first.text
    choose_second = client.post(
        f"/api/v1/door-to-door/history/{history_id}/chosen",
        json={"option_id": second["id"], "option_label": second["label"], "option_summary": {}},
        headers=headers,
    )
    assert choose_second.status_code == 200, choose_second.text

    history_response = client.get(f"/api/v1/door-to-door/history?watch_id={watch_id}", headers=headers)
    assert history_response.status_code == 200, history_response.text
    history_items = history_response.json()
    assert history_items
    target = next(item for item in history_items if item["id"] == history_id)
    assert target["chosen_option_id"] == second["id"]


def test_search_response_includes_map_capabilities_with_all_canonical_keys(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client, "map-capabilities@viru.dev")
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    capabilities = body.get("map_capabilities")
    assert capabilities is not None

    canonical_keys = {
        "navigation", "traffic", "transit", "alternatives",
        "street_view_preview", "saved_places", "nearby_pois",
        "offline", "incidents", "eco_route",
    }
    assert set(capabilities.keys()) == canonical_keys

    for key in canonical_keys:
        cap = capabilities[key]
        assert cap["state"] in ("available", "partial", "planned", "unavailable")
        assert cap["source_type"] in (
            "api", "open_data", "aggregator", "deeplink", "scraper",
            "mock", "estimate", "maps", "external_deeplink", "none",
        )
        assert cap["confidence"] in ("live", "cached", "estimated", "deeplink", "unavailable")
        assert "last_checked_at" in cap
        # why_missing must be present (null when capability is available)
        assert "why_missing" in cap

    # With mock enabled and options present, alternatives should be available
    assert capabilities["alternatives"]["state"] == "available"
    # navigation depends on google_routes which is disabled here
    assert capabilities["navigation"]["state"] == "planned"
    assert capabilities["navigation"]["why_missing"] is not None


def test_history_tolerates_corrupted_summary_json(client: TestClient, monkeypatch) -> None:
    _set_provider_env(monkeypatch, mock=True, real=False, scrapers=False)
    headers = _auth_headers(client, "history-corrupt-json@viru.dev")
    watch_id = _create_watch(client, headers)

    search_response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)
    assert search_response.status_code == 200, search_response.text
    history_id = search_response.json()["summary"]["history_id"]
    assert history_id

    db, db_gen = _open_test_db_session()
    try:
        row = db.get(DoorToDoorSearchHistory, history_id)
        assert row is not None
        row.summary_json = "{broken-json"
        db.commit()
    finally:
        db_gen.close()

    history_response = client.get(f"/api/v1/door-to-door/history?watch_id={watch_id}", headers=headers)
    assert history_response.status_code == 200, history_response.text
    history_items = history_response.json()
    assert history_items
    target = next(item for item in history_items if item["id"] == history_id)
    assert target["recommended_option_id"] is None
    assert target["recommended_label"] is None
    assert target["total_price_min"] is None
    assert target["total_price_max"] is None
