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
