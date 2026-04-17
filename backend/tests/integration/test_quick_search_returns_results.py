from datetime import date, timedelta

from fastapi.testclient import TestClient

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight


class _FakeQuickSearchProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000) -> list[ProviderFlight]:
        if origin == "AGP" and destination == "DUB":
            return [
                ProviderFlight(
                    price=39.99,
                    currency="EUR",
                    departure_time_local="08:40",
                    captured_at=utc_now_naive(),
                    source="fake-quick-search-provider",
                )
            ]
        return []


def test_quick_search_valid_route_returns_at_least_one_result(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(search_api, "provider", _FakeQuickSearchProvider())

    travel_date = str(date.today() + timedelta(days=21))
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) >= 1
    first = payload["results"][0]
    assert first["origin"] == "AGP"
    assert first["destination"] == "DUB"
    assert first["travel_date"] == travel_date
    assert first["price_total"] == 39.99
    assert first["source"] == "fake-quick-search-provider"
