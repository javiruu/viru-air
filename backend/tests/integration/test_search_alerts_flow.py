from datetime import date, timedelta

from fastapi.testclient import TestClient

import app.api.v1.search as search_api
import app.api.v1.watchlist as watchlist_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from tests.helpers import register_and_token


class _FakeSearchProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000) -> list[ProviderFlight]:
        if origin == "MAD" and destination == "DUB":
            return [
                ProviderFlight(
                    price=41.0,
                    currency="EUR",
                    departure_time_local="10:20",
                    captured_at=utc_now_naive(),
                    source="fake-search-provider",
                )
            ]
        return []


class _PriceSequenceProvider:
    def __init__(self, prices: list[float]) -> None:
        self._prices = prices
        self._index = 0

    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        value = self._prices[min(self._index, len(self._prices) - 1)]
        self._index += 1
        return [
            ProviderFlight(
                price=value,
                currency="EUR",
                departure_time_local="09:00",
                captured_at=utc_now_naive(),
                source="sequence-provider",
            )
        ]


def test_quick_search_and_alert_rule(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(search_api, "provider", _FakeSearchProvider())

    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    search = client.post(
        "/api/v1/search/quick",
        params={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date": str(date.today() + timedelta(days=10)),
        },
        headers=headers,
    )
    assert search.status_code == 200
    assert len(search.json()["results"]) >= 1

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=12)),
            "target_price": 35,
        },
    )
    watch_id = create.json()["id"]

    rule = client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "threshold_below",
            "threshold_value": 30,
            "notify_on_every_change": False,
            "cooldown_minutes": 60,
        },
    )
    assert rule.status_code == 200

    rules = client.get(f"/api/v1/alerts/rules?watch_id={watch_id}", headers=headers)
    assert rules.status_code == 200
    assert len(rules.json()) == 1


def test_search_save_result_creates_or_reuses_watch(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(search_api, "provider", _FakeSearchProvider())

    token = register_and_token(client, email="save-result@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    travel_date = str(date.today() + timedelta(days=20))

    first = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date": travel_date,
            "price_total": 39.5,
        },
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["created_or_existing"] == "created"
    assert first_payload["watch_id"]

    second = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date": travel_date,
            "price_total": 39.5,
        },
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["created_or_existing"] == "existing"
    assert second_payload["watch_id"] == first_payload["watch_id"]


def test_alert_rule_min_change_pct_is_applied(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _PriceSequenceProvider([100.0, 103.0, 110.0]))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)

    token = register_and_token(client, email="min-change@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=25)),
            "target_price": 35,
        },
    )
    watch_id = create.json()["id"]

    rule = client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "every_change",
            "notify_on_every_change": True,
            "cooldown_minutes": 60,
            "min_change_pct": 5,
        },
    )
    assert rule.status_code == 200
    assert rule.json()["min_change_pct"] == 5.0

    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200
    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200
    first_eval = client.post("/api/v1/alerts/evaluate", headers=headers, json={"watch_id": watch_id})
    assert first_eval.status_code == 200
    assert first_eval.json()["created"] == 0

    assert client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers).status_code == 200
    second_eval = client.post("/api/v1/alerts/evaluate", headers=headers, json={"watch_id": watch_id})
    assert second_eval.status_code == 200
    assert second_eval.json()["created"] == 1
