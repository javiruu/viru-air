from datetime import date, timedelta

from fastapi.testclient import TestClient

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight, ProviderSourceFetchError
from app.services.quick_search_execution import _CACHE


class _ProviderWithAvailabilityFailure:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        if origin == "MAD" and destination == "DUB":
            return ProviderFetchResult(
                flights=[
                    ProviderFlight(
                        price=44.99,
                        currency="EUR",
                        departure_time_local="08:10",
                        captured_at=utc_now_naive(),
                        source="ryanair-public-fares",
                    )
                ],
                warnings=["ryanair_availability_failed_partial"],
            )
        return ProviderFetchResult(flights=[], warnings=[])


class _ProviderTotallyUnavailable:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        raise ProviderSourceFetchError(
            warning_codes=[
                "ryanair_availability_failed",
                "ryanair_fares_failed",
                "ryanair_provider_unavailable_total",
            ],
            message="provider unavailable",
        )


class _ProviderWithRepeatedPartialWarnings:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        return ProviderFetchResult(
            flights=[],
            warnings=["ryanair_availability_failed_partial"],
        )


def test_quick_search_returns_results_when_availability_degrades(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    monkeypatch.setattr(search_api, "provider", _ProviderWithAvailabilityFailure())

    travel_date = str(date.today() + timedelta(days=21))
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "MAD", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) == 1
    assert payload["results"][0]["source"] == "ryanair-public-fares"
    assert "ryanair_availability_failed_partial" in payload["filters"]["warnings"]
    assert any(item["code"] == "provider_partial_results_served" for item in payload["meta"]["warnings_structured"])


def test_quick_search_exposes_total_provider_outage(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    monkeypatch.setattr(search_api, "provider", _ProviderTotallyUnavailable())

    travel_date = str(date.today() + timedelta(days=21))
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "MAD", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["results"] == []
    assert "ryanair_provider_unavailable_total" in payload["filters"]["warnings"]
    assert any(item["code"] == "ryanair_provider_unavailable_total" for item in payload["meta"]["warnings_structured"])


def test_quick_search_dedupes_repeated_partial_warnings(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    monkeypatch.setattr(search_api, "provider", _ProviderWithRepeatedPartialWarnings())

    travel_date = str(date.today() + timedelta(days=21))
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "MAD", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 1, "flex_after": 1},
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["results"] == []
    assert payload["filters"]["warnings"] == ["ryanair_availability_failed_partial"]
    assert [
        item["code"]
        for item in payload["meta"]["warnings_structured"]
        if item["code"] == "ryanair_availability_failed_partial"
    ] == ["ryanair_availability_failed_partial"]
