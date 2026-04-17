from datetime import date, timedelta

from fastapi.testclient import TestClient

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from tests.helpers import register_and_token


class _FakeRealisticQuickSearchProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000) -> list[ProviderFlight]:
        if origin == "AGP" and destination == "DUB":
            return [
                ProviderFlight(
                    price=37.99,
                    currency="EUR",
                    departure_time_local="07:10",
                    captured_at=utc_now_naive(),
                    source="fake-realistic-provider",
                ),
                ProviderFlight(
                    price=42.50,
                    currency="EUR",
                    departure_time_local="18:25",
                    captured_at=utc_now_naive(),
                    source="fake-realistic-provider",
                ),
            ]
        return []


def test_quick_search_realistic_happy_path_returns_results(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(search_api, "provider", _FakeRealisticQuickSearchProvider())

    token = register_and_token(client, email="realistic-quick-search@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    travel_date = str(date.today() + timedelta(days=20))

    seeds = client.get("/api/v1/airports/seeds", headers=headers)
    assert seeds.status_code == 200
    seed_codes = {item["iata"] for item in seeds.json()["items"]}
    assert "AGP" in seed_codes
    assert "DUB" in seed_codes

    deeplink = client.get(
        "/api/v1/search/deeplink",
        params={
            "origin_iata": "AGP",
            "destination_iata": "DUB",
            "date_out": travel_date,
            "adults": 1,
            "teens": 0,
            "children": 0,
            "infants": 0,
            "locale": "es-es",
        },
        headers=headers,
    )
    assert deeplink.status_code == 200
    deeplink_body = deeplink.json()
    assert deeplink_body["origin_iata"] == "AGP"
    assert deeplink_body["destination_iata"] == "DUB"
    assert deeplink_body["date_out"] == travel_date
    assert "ryanair.com" in deeplink_body["url"]

    quick_search = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
            "constraints": {"strict_filters": True},
            "execution": {"max_pairs": 12, "max_requests": 24, "timeout_ms": 3000, "concurrency_limit": 4},
        },
        headers=headers,
    )
    assert quick_search.status_code == 200

    payload = quick_search.json()
    assert payload["meta"]["query_trace_id"].startswith("qs_")
    assert payload["query"]["origin"]["seed_iata"] == "AGP"
    assert payload["query"]["destination"]["seed_iata"] == "DUB"
    assert len(payload["results"]) >= 1

    first = payload["results"][0]
    assert first["origin"] == "AGP"
    assert first["destination"] == "DUB"
    assert first["travel_date"] == travel_date
    assert first["source"] == "fake-realistic-provider"
    assert first["price_total"] == 37.99
    assert first["ranking_score"] == first["score"]["final_score"]
