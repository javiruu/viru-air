from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.door_to_door.domain.risk import calculate_risk_level
from app.door_to_door.domain.scoring import score_itinerary
from app.door_to_door.providers.base import DoorToDoorProvider, DoorToDoorProviderQuery
from app.door_to_door.schemas import DoorToDoorOptionOut
from app.door_to_door.services.search_service import DoorToDoorSearchService
from tests.helpers import register_and_token


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


def test_search_returns_mock_options(client: TestClient) -> None:
    headers = _auth_headers(client)
    watch_id = _create_watch(client, headers)

    response = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["flight"]["origin_airport"] == "AGP"
    assert body["flight"]["destination_airport"] == "TSF"
    assert body["flight"]["flight_time_confidence"] in {"live", "estimated"}
    assert len(body["options"]) >= 3
    assert body["summary"]["recommended_option_id"]
    assert body["summary"]["history_id"]


def test_source_metadata_is_present(client: TestClient) -> None:
    headers = _auth_headers(client, "source@viru.dev")
    watch_id = _create_watch(client, headers)

    body = client.post("/api/v1/door-to-door/search", json=_search_payload(watch_id), headers=headers).json()
    source = body["options"][0]["sources"][0]

    assert source["provider"]
    assert source["source_provider"]
    assert source["source_type"] == "mock"
    assert source["confidence"] == "estimated"
    assert source["checked_at"]


def test_partial_provider_warning(client: TestClient, monkeypatch) -> None:
    from app.door_to_door.api import routes

    class FailingProvider(DoorToDoorProvider):
        provider_name = "failing_provider"
        source_type = "api"

        async def search(self, query: DoorToDoorProviderQuery) -> list[DoorToDoorOptionOut]:
            raise RuntimeError("provider down")

        async def healthcheck(self):  # pragma: no cover - not used in this path
            raise RuntimeError("provider down")

    class MixedService(DoorToDoorSearchService):
        def __init__(self) -> None:
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


def test_score_prefers_safer_route_when_buffer_is_low() -> None:
    safe = score_itinerary(55, 520, 150, 2, "low", "estimated")
    risky = score_itinerary(30, 420, 65, 1, "high", "estimated")
    assert safe > risky


def test_high_risk_when_airport_buffer_under_90() -> None:
    assert calculate_risk_level(89, 1, "estimated") == "high"


def test_suggestions_saved_location_history_and_chosen_option(client: TestClient) -> None:
    headers = _auth_headers(client, "history@viru.dev")
    watch_id = _create_watch(client, headers)

    suggestions = client.get("/api/v1/door-to-door/suggestions?q=Almería", headers=headers)
    assert suggestions.status_code == 200
    assert suggestions.json()[0]["label"] == "Almería"

    payload = _search_payload(watch_id)
    payload["save_origin_as_default"] = True
    search = client.post("/api/v1/door-to-door/search", json=payload, headers=headers)
    assert search.status_code == 200, search.text
    body = search.json()

    saved = client.get("/api/v1/door-to-door/saved-location", headers=headers)
    assert saved.status_code == 200
    assert saved.json()["label"] == "Almería"

    history = client.get(f"/api/v1/door-to-door/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    assert history.json()

    option = body["options"][0]
    chosen = client.post(
        f"/api/v1/door-to-door/history/{body['summary']['history_id']}/chosen",
        json={
            "option_id": option["id"],
            "option_label": option["label"],
            "option_summary": {"risk_level": option["risk_level"]},
        },
        headers=headers,
    )
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["option_id"] == option["id"]
