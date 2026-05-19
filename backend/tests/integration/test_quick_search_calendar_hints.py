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
        if day == 5:
            return [
                ProviderFlight(
                    price=60.0,
                    currency="EUR",
                    departure_time_local="08:10",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-provider",
                )
            ]
        if day == 10:
            return [
                ProviderFlight(
                    price=120.0,
                    currency="EUR",
                    departure_time_local="08:40",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-provider",
                )
            ]
        if day == 15:
            return [
                ProviderFlight(
                    price=210.0,
                    currency="EUR",
                    departure_time_local="09:20",
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
