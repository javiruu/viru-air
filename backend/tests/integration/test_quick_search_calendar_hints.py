from fastapi.testclient import TestClient

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from app.services.quick_search_execution import _CACHE


class _CalendarHintsProvider:
    def __init__(self) -> None:
        self.calls = 0

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        self.calls += 1
        day = int(travel_date.split("-")[2])
        route = f"{origin}-{destination}"
        route_prices: dict[str, dict[int, float]] = {
            "MAD-DUB": {5: 60.0, 10: 120.0, 15: 210.0},
            "BCN-DUB": {5: 80.0, 10: 110.0, 15: 160.0},
            "AGP-DUB": {5: 95.0, 10: 100.0, 15: 150.0},
        }
        route_day_prices = route_prices.get(route, {})
        if day in route_day_prices:
            return [
                ProviderFlight(
                    price=route_day_prices[day],
                    currency="EUR",
                    departure_time_local="08:10",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-provider",
                )
            ]
        return []


def test_quick_search_calendar_hints_returns_month_with_buckets_and_cache(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    fake_provider = _CalendarHintsProvider()
    monkeypatch.setattr(search_api, "provider", fake_provider)

    payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "month": "2030-06",
        "adults": 1,
    }

    response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 30
    assert data["meta"]["cache_hit"] is False
    assert data["meta"]["cache_ttl_sec"] == 600
    assert data["meta"]["partial"] is False
    assert data["meta"]["scope_mode"] == "iata"
    assert data["meta"]["aggregation_mode"] == "min"

    days_by_iso = {day["date"]: day for day in data["days"]}
    assert days_by_iso["2030-06-05"]["bucket"] == "low"
    assert days_by_iso["2030-06-10"]["bucket"] == "mid"
    assert days_by_iso["2030-06-15"]["bucket"] == "high"
    assert days_by_iso["2030-06-20"]["bucket"] == "none"
    assert days_by_iso["2030-06-20"]["no_data_reason"] == "no_fare_data"

    calls_after_first_request = fake_provider.calls
    assert calls_after_first_request > 0

    second_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["meta"]["cache_hit"] is True
    assert fake_provider.calls == calls_after_first_request


def test_quick_search_calendar_hints_country_scope_supports_aggregation_modes(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    fake_provider = _CalendarHintsProvider()
    monkeypatch.setattr(search_api, "provider", fake_provider)

    base_payload = {
        "origin_iata": ["MAD", "BCN", "AGP"],
        "destination_iata": "DUB",
        "month": "2030-06",
        "adults": 1,
    }

    min_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "min"},
    )
    assert min_response.status_code == 200
    min_data = min_response.json()
    assert min_data["meta"]["cache_hit"] is False
    assert min_data["meta"]["scope_mode"] == "country_mixed"
    assert min_data["meta"]["aggregation_mode"] == "min"
    assert min_data["meta"]["ranked_routes_count"] >= 1
    assert min_data["meta"]["ranked_airports"]["origin_count"] >= 1
    min_days_by_iso = {day["date"]: day for day in min_data["days"]}
    assert min_days_by_iso["2030-06-10"]["min_price"] == 100.0

    min_cached_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "min"},
    )
    assert min_cached_response.status_code == 200
    assert min_cached_response.json()["meta"]["cache_hit"] is True

    median_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "median"},
    )
    assert median_response.status_code == 200
    median_data = median_response.json()
    assert median_data["meta"]["cache_hit"] is False
    assert median_data["meta"]["scope_mode"] == "country_mixed"
    assert median_data["meta"]["aggregation_mode"] == "median"
    median_days_by_iso = {day["date"]: day for day in median_data["days"]}
    assert median_days_by_iso["2030-06-10"]["min_price"] == 110.0

    fixed_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "fixed_route"},
    )
    assert fixed_response.status_code == 200
    fixed_data = fixed_response.json()
    assert fixed_data["meta"]["scope_mode"] == "country_mixed"
    assert fixed_data["meta"]["aggregation_mode"] == "fixed_route"
    fixed_days_by_iso = {day["date"]: day for day in fixed_data["days"]}
    assert fixed_days_by_iso["2030-06-10"]["min_price"] == 100.0

    country_country_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            "origin_iata": ["MAD", "BCN"],
            "destination_iata": ["DUB", "AGP"],
            "month": "2030-06",
            "adults": 1,
            "aggregation_mode": "min",
        },
    )
    assert country_country_response.status_code == 200
    country_country_data = country_country_response.json()
    assert country_country_data["meta"]["scope_mode"] == "country_country"
