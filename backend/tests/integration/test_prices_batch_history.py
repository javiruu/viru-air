from datetime import date, timedelta

import app.api.v1.watchlist as watchlist_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from fastapi.testclient import TestClient

from tests.helpers import register_and_token


class _FakeProvider:
    def __init__(self) -> None:
        self._price_seed = 40

    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        self._price_seed += 1
        return [
            ProviderFlight(
                price=float(self._price_seed),
                currency="EUR",
                departure_time_local="09:15",
                captured_at=utc_now_naive(),
                source="fake-provider",
            )
        ]


def _create_watch(client: TestClient, headers: dict[str, str], origin: str, destination: str, days: int) -> str:
    response = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": origin,
            "destination_iata": destination,
            "travel_date_local": str(date.today() + timedelta(days=days)),
            "target_price": 50,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_batch_history_empty_watch_ids_returns_empty(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="batch-empty@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/v1/prices/history/batch", headers=headers, json={"watch_ids": []})
    assert response.status_code == 200
    assert response.json() == []


def test_batch_history_mixed_watch_ids_returns_only_owned(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token_owner = register_and_token(client, email="batch-owner@viru.dev")
    token_other = register_and_token(client, email="batch-other@viru.dev")

    owner_headers = {"Authorization": f"Bearer {token_owner}"}
    other_headers = {"Authorization": f"Bearer {token_other}"}

    owned_watch_id = _create_watch(client, owner_headers, "MAD", "DUB", 30)
    foreign_watch_id = _create_watch(client, other_headers, "AGP", "TSF", 31)

    refresh_owned = client.post(f"/api/v1/watchlist/{owned_watch_id}/refresh-now", headers=owner_headers)
    assert refresh_owned.status_code == 200

    refresh_foreign = client.post(f"/api/v1/watchlist/{foreign_watch_id}/refresh-now", headers=other_headers)
    assert refresh_foreign.status_code == 200

    response = client.post(
        "/api/v1/prices/history/batch",
        headers=owner_headers,
        json={"watch_ids": [owned_watch_id, foreign_watch_id]},
    )
    assert response.status_code == 200

    payload = response.json()
    assert len(payload) >= 1
    assert {item["watch_id"] for item in payload} == {owned_watch_id}


def test_batch_history_duplicate_watch_ids_do_not_duplicate_rows(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="batch-dup@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    watch_id = _create_watch(client, headers, "MAD", "BLQ", 29)

    refresh = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    assert refresh.status_code == 200

    single = client.post(
        "/api/v1/prices/history/batch",
        headers=headers,
        json={"watch_ids": [watch_id]},
    )
    assert single.status_code == 200

    duplicated = client.post(
        "/api/v1/prices/history/batch",
        headers=headers,
        json={"watch_ids": [watch_id, watch_id, watch_id]},
    )
    assert duplicated.status_code == 200
    assert duplicated.json() == single.json()


def test_batch_history_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/prices/history/batch", json={"watch_ids": []})
    assert response.status_code == 401


def test_batch_history_invalid_payload_returns_422(client: TestClient) -> None:
    token = register_and_token(client, email="batch-422@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    too_many_ids = [f"watch-{idx}" for idx in range(501)]
    response = client.post(
        "/api/v1/prices/history/batch",
        headers=headers,
        json={"watch_ids": too_many_ids},
    )
    assert response.status_code == 422


def test_batch_history_rejects_payload_too_large_response(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="batch-too-large@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    watch_one = _create_watch(client, headers, "MAD", "DUB", 35)
    watch_two = _create_watch(client, headers, "MAD", "BLQ", 36)

    assert client.post(f"/api/v1/watchlist/{watch_one}/refresh-now", headers=headers).status_code == 200
    assert client.post(f"/api/v1/watchlist/{watch_two}/refresh-now", headers=headers).status_code == 200

    response = client.post(
        "/api/v1/prices/history/batch",
        headers=headers,
        json={"watch_ids": [watch_one, watch_two], "max_rows": 1},
    )
    assert response.status_code == 413


def test_batch_history_can_filter_by_captured_since(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="batch-since@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    watch_id = _create_watch(client, headers, "AGP", "TSF", 37)
    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200

    without_filter = client.post(
        "/api/v1/prices/history/batch",
        headers=headers,
        json={"watch_ids": [watch_id]},
    )
    assert without_filter.status_code == 200
    assert len(without_filter.json()) >= 1

    with_future_filter = client.post(
        "/api/v1/prices/history/batch",
        headers=headers,
        json={"watch_ids": [watch_id], "captured_since_utc": "2999-01-01T00:00:00"},
    )
    assert with_future_filter.status_code == 200
    assert with_future_filter.json() == []


def test_prices_summary_returns_aggregates(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="summary@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    watch_id = _create_watch(client, headers, "MAD", "DUB", 38)

    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200
    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200

    summary = client.get(f"/api/v1/prices/summary?watch_id={watch_id}", headers=headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["watch_id"] == watch_id
    assert payload["count"] == 2
    assert payload["min_price"] <= payload["max_price"]
    assert payload["latest_price"] is not None
