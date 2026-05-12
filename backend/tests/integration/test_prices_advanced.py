from datetime import date, timedelta

import app.api.v1.watchlist as watchlist_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from fastapi.testclient import TestClient

from tests.helpers import register_and_token


class _FakeProvider:
    def __init__(self, currency: str = "EUR") -> None:
        self._price_seed = 90
        self._currency = currency

    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        self._price_seed += 5
        return [
            ProviderFlight(
                price=float(self._price_seed),
                currency=self._currency,
                departure_time_local="10:20",
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


def _error_code(payload: dict) -> str | None:
    if isinstance(payload.get("code"), str):
        return payload["code"]
    if "detail" in payload and isinstance(payload["detail"], str):
        return payload["detail"]
    if isinstance(payload.get("error"), dict):
        code = payload["error"].get("code")
        return code if isinstance(code, str) else None
    return None


def test_prices_calendar_empty_returns_days_empty(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="calendar-empty@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    watch_id = _create_watch(client, headers, "MAD", "DUB", 45)

    response = client.get(f"/api/v1/prices/calendar?watch_id={watch_id}", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["watch_id"] == watch_id
    assert payload["days"] == []


def test_prices_calendar_with_snapshots_returns_day_stats(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider(currency="EUR"))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="calendar-data@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    watch_id = _create_watch(client, headers, "AGP", "TSF", 46)

    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200
    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200

    response = client.get(f"/api/v1/prices/calendar?watch_id={watch_id}", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["watch_id"] == watch_id
    assert payload["currency"] == "EUR"
    assert len(payload["days"]) >= 1
    first = payload["days"][0]
    assert first["snapshot_count"] >= 1
    assert first["min_price"] <= first["avg_price"] <= first["max_price"]
    assert isinstance(first["is_daily_min"], bool)
    assert isinstance(first["is_daily_max"], bool)


def test_prices_compare_two_watches_returns_stats(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider(currency="EUR"))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="compare-two@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    watch_a = _create_watch(client, headers, "MAD", "DUB", 47)
    watch_b = _create_watch(client, headers, "MAD", "BLQ", 48)

    assert client.post(f"/api/v1/watchlist/{watch_a}/refresh-now", headers=headers).status_code == 200
    assert client.post(f"/api/v1/watchlist/{watch_b}/refresh-now", headers=headers).status_code == 200

    response = client.get(f"/api/v1/prices/compare?watch_ids={watch_a},{watch_b}", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["currency_mode"] == "single"
    assert len(payload["watches"]) == 2
    assert len(payload["points"]) == 2


def test_prices_compare_rejects_more_than_four(client: TestClient) -> None:
    token = register_and_token(client, email="compare-max@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/prices/compare?watch_ids=a,b,c,d,e", headers=headers)
    assert response.status_code == 400
    assert _error_code(response.json()) == "compare_watch_limit_exceeded"


def test_prices_compare_rejects_foreign_watch(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider(currency="EUR"))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    owner = register_and_token(client, email="compare-owner@viru.dev")
    other = register_and_token(client, email="compare-other@viru.dev")
    owner_headers = {"Authorization": f"Bearer {owner}"}
    other_headers = {"Authorization": f"Bearer {other}"}
    owner_watch = _create_watch(client, owner_headers, "MAD", "DUB", 49)
    foreign_watch = _create_watch(client, other_headers, "AGP", "TSF", 50)

    response = client.get(
        f"/api/v1/prices/compare?watch_ids={owner_watch},{foreign_watch}",
        headers=owner_headers,
    )
    assert response.status_code == 403
    assert _error_code(response.json()) == "compare_contains_foreign_or_missing_watch"


def test_prices_compare_mixed_currency_mode(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="compare-mixed@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    watch_a = _create_watch(client, headers, "MAD", "DUB", 51)
    watch_b = _create_watch(client, headers, "MAD", "BLQ", 52)

    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider(currency="EUR"))
    assert client.post(f"/api/v1/watchlist/{watch_a}/refresh-now", headers=headers).status_code == 200
    monkeypatch.setattr(watchlist_api, "provider", _FakeProvider(currency="USD"))
    assert client.post(f"/api/v1/watchlist/{watch_b}/refresh-now", headers=headers).status_code == 200

    response = client.get(f"/api/v1/prices/compare?watch_ids={watch_a},{watch_b}", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["currency_mode"] == "mixed"
