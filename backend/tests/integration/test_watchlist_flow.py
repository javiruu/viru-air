from datetime import date, timedelta

from app.core.time import utc_now_naive

from fastapi.testclient import TestClient

import app.api.v1.watchlist as watchlist_api
from app.domain.entities import ProviderFetchResult, ProviderFlight
from tests.helpers import register_and_token


class _FakeProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        return [
            ProviderFlight(
                price=44.0,
                currency="EUR",
                departure_time_local="09:15",
                captured_at=utc_now_naive(),
                source="fake-provider",
            )
        ]


class _FakeProviderFetchResult:
    def get_flights(self, origin: str, destination: str, travel_date: str) -> ProviderFetchResult:
        return ProviderFetchResult(
            flights=[
                ProviderFlight(
                    price=47.0,
                    currency="EUR",
                    departure_time_local="07:40",
                    captured_at=utc_now_naive(),
                    source="fake-provider-result",
                )
            ],
            warnings=[],
        )


def test_watchlist_create_list_and_refresh(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=30)),
            "target_price": 40,
        },
    )
    assert create.status_code == 200
    watch_id = create.json()["id"]

    listing = client.get("/api/v1/watchlist", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    refresh = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    assert refresh.status_code == 200

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) >= 1

    detail = client.get(f"/api/v1/watchlist/{watch_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == watch_id
    assert detail.json()["latest_snapshot"] is not None


def test_watchlist_refresh_supports_provider_fetch_result(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProviderFetchResult())

    token = register_and_token(client, email="provider-fetch-result@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=31)),
            "target_price": 45,
        },
    )
    assert create.status_code == 200
    watch_id = create.json()["id"]

    refresh = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    assert refresh.status_code == 200

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) >= 1


def test_watchlist_create_duplicate_returns_409(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="duplicate-watch@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "travel_date_local": str(date.today() + timedelta(days=45)),
        "target_price": 55,
    }

    first = client.post("/api/v1/watchlist", headers=headers, json=payload)
    assert first.status_code == 200

    duplicated = client.post("/api/v1/watchlist", headers=headers, json=payload)
    assert duplicated.status_code == 409
    body = duplicated.json()
    assert body.get("code") == "watch_already_exists" or body.get("detail") == "watch_already_exists"


def test_watchlist_refresh_bulk_returns_summary(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="bulk-refresh@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create_a = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=33)),
        },
    )
    create_b = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "BCN",
            "destination_iata": "LIS",
            "travel_date_local": str(date.today() + timedelta(days=34)),
        },
    )
    watch_a = create_a.json()["id"]
    watch_b = create_b.json()["id"]

    bulk = client.post(
        "/api/v1/watchlist/refresh-bulk",
        headers=headers,
        json={"watch_ids": [watch_a, watch_b, "missing-watch-id"]},
    )
    assert bulk.status_code == 200
    payload = bulk.json()
    assert payload["requested"] == 3
    assert set(payload["refreshed"]) == {watch_a, watch_b}
    assert any(item["code"] == "watch_not_found" for item in payload["failed"])


def test_watchlist_status_bulk_returns_partial_summary(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="bulk-status@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create_a = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=37)),
        },
    )
    create_b = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "BCN",
            "destination_iata": "LIS",
            "travel_date_local": str(date.today() + timedelta(days=38)),
        },
    )
    watch_a = create_a.json()["id"]
    watch_b = create_b.json()["id"]

    bulk = client.post(
        "/api/v1/watchlist/status-bulk",
        headers=headers,
        json={"watch_ids": [watch_a, watch_b, "missing-watch-id"], "status": "paused"},
    )
    assert bulk.status_code == 200
    payload = bulk.json()
    assert payload["requested"] == 3
    assert set(payload["updated_ids"]) == {watch_a, watch_b}
    assert any(item["code"] == "watch_not_found" for item in payload["failed"])


def test_watchlist_delete_bulk_returns_partial_summary(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())

    token = register_and_token(client, email="bulk-delete@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create_a = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=39)),
        },
    )
    create_b = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "BCN",
            "destination_iata": "LIS",
            "travel_date_local": str(date.today() + timedelta(days=40)),
        },
    )
    watch_a = create_a.json()["id"]
    watch_b = create_b.json()["id"]

    bulk = client.post(
        "/api/v1/watchlist/delete-bulk",
        headers=headers,
        json={"watch_ids": [watch_a, watch_b, "missing-watch-id"]},
    )
    assert bulk.status_code == 200
    payload = bulk.json()
    assert payload["requested"] == 3
    assert set(payload["deleted_ids"]) == {watch_a, watch_b}
    assert any(item["code"] == "watch_not_found" for item in payload["failed"])


def test_watchlist_status_bulk_rejects_invalid_payload(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    token = register_and_token(client, email="bulk-status-invalid@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    invalid_status = client.post(
        "/api/v1/watchlist/status-bulk",
        headers=headers,
        json={"watch_ids": ["watch-a"], "status": "invalid"},
    )
    assert invalid_status.status_code == 422

    empty_ids = client.post(
        "/api/v1/watchlist/status-bulk",
        headers=headers,
        json={"watch_ids": [], "status": "paused"},
    )
    assert empty_ids.status_code == 422
