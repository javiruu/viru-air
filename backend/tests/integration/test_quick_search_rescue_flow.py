from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.infrastructure.airports_catalog import ExpandedAirportCandidate
from app.services.quick_search_execution import _CACHE
from app.services.quick_search_expansion import SideExpansionResult, SideExpansionSummary


def _build_side(
    *,
    side: str,
    seed_iata: str,
    include_nearby: bool,
    radius_km: int,
    max_candidates: int,
) -> SideExpansionResult:
    nearby_code = "AGP" if side == "origin" else "LIS"
    candidates = [
        ExpandedAirportCandidate(
            seed_iata=seed_iata,
            expanded_iata=seed_iata,
            is_seed=True,
            distance_km=0.0,
            candidate_reason="seed",
            source_of_expansion="test",
        )
    ]
    if include_nearby:
        candidates.append(
            ExpandedAirportCandidate(
                seed_iata=seed_iata,
                expanded_iata=nearby_code,
                is_seed=False,
                distance_km=42.0,
                candidate_reason="nearby",
                source_of_expansion="test",
            )
        )
    return SideExpansionResult(
        side=side,
        candidates=candidates[:max(1, max_candidates)],
        summary=SideExpansionSummary(
            side=side,
            seed_iata=seed_iata,
            include_nearby_applied=include_nearby,
            radius_km_effective=radius_km,
            max_candidates_effective=max(1, max_candidates),
            exclusions_applied=[],
            total_candidates_before_limit=len(candidates),
            total_candidates_after_limit=min(len(candidates), max(1, max_candidates)),
        ),
    )


def _fake_expand_search_sides(
    *,
    origin_seed_iata: str,
    destination_seed_iata: str,
    include_nearby_origins: bool,
    include_nearby_destinations: bool,
    origin_radius_km: int,
    destination_radius_km: int,
    origin_max_candidates: int,
    destination_max_candidates: int,
    exclude_origins: list[str],
    exclude_destinations: list[str],
):
    del exclude_origins, exclude_destinations
    return (
        _build_side(
            side="origin",
            seed_iata=origin_seed_iata,
            include_nearby=include_nearby_origins,
            radius_km=origin_radius_km,
            max_candidates=origin_max_candidates,
        ),
        _build_side(
            side="destination",
            seed_iata=destination_seed_iata,
            include_nearby=include_nearby_destinations,
            radius_km=destination_radius_km,
            max_candidates=destination_max_candidates,
        ),
    )


def _base_payload(target_date: str) -> dict:
    return {
        "origin": {"seed_iata": "MAD", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
        "destination": {"seed_iata": "BCN", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
        "travel": {"date": target_date, "flex_before": 0, "flex_after": 0},
        "constraints": {
            "departure_window": {"after": "07:00", "before": "22:00"},
            "strict_filters": True,
            "include_stops": False,
            "max_stops": 0,
            "soft_filters_weight": 0.6,
        },
    }


class _ProviderDateRescue:
    def __init__(self, target_date: date) -> None:
        self._target = target_date

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        del timeout_ms
        query_date = date.fromisoformat(travel_date)
        if origin == "MAD" and destination == "BCN" and query_date == self._target + timedelta(days=1):
            return ProviderFetchResult(
                flights=[
                    ProviderFlight(
                        price=79.0,
                        currency="EUR",
                        departure_time_local="09:30",
                        captured_at=utc_now_naive(),
                        source="fake-date-rescue",
                    )
                ],
                warnings=["ryanair_availability_failed_partial"],
            )
        return ProviderFetchResult(flights=[], warnings=["ryanair_availability_failed_partial"])


class _ProviderNearbyRescue:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        del travel_date, timeout_ms
        if origin == "AGP" and destination == "LIS":
            return ProviderFetchResult(
                flights=[
                    ProviderFlight(
                        price=55.5,
                        currency="EUR",
                        departure_time_local="11:05",
                        captured_at=utc_now_naive(),
                        source="fake-nearby-rescue",
                    )
                ],
                warnings=["ryanair_availability_failed_partial"],
            )
        return ProviderFetchResult(flights=[], warnings=["ryanair_availability_failed_partial"])


class _ProviderNeverRecovers:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        del origin, destination, travel_date, timeout_ms
        return ProviderFetchResult(flights=[], warnings=["ryanair_availability_failed_partial"])


class _ProviderExactSuccess:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        del travel_date, timeout_ms
        if origin == "MAD" and destination == "BCN":
            return ProviderFetchResult(
                flights=[
                    ProviderFlight(
                        price=41.2,
                        currency="EUR",
                        departure_time_local="10:40",
                        captured_at=utc_now_naive(),
                        source="fake-exact-success",
                    )
                ],
                warnings=[],
            )
        return ProviderFetchResult(flights=[], warnings=[])


def test_quick_search_rescue_date_finds_results(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    target_date = date.today() + timedelta(days=21)
    monkeypatch.setattr(search_api, "provider", _ProviderDateRescue(target_date))
    monkeypatch.setattr(search_api, "expand_search_sides", _fake_expand_search_sides)

    response = client.post("/api/v1/search/quick", json=_base_payload(str(target_date)))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) >= 1
    assert payload["meta"]["rescue"]["attempted"] is True
    assert payload["meta"]["rescue"]["winning_step"] == "pass_3_rescue_date"
    assert "date_flex_auto" in payload["filters"]["relaxed"]
    assert "rescue_mode_applied" not in payload["filters"]["warnings"]
    assert [item["step"] for item in payload["meta"]["rescue"]["pass_summaries"][:2]] == [
        "pass_1_exact",
        "pass_2_rescue_budget_boost",
    ]


def test_quick_search_rescue_nearby_finds_results(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    target_date = date.today() + timedelta(days=21)
    monkeypatch.setattr(search_api, "provider", _ProviderNearbyRescue())
    monkeypatch.setattr(search_api, "expand_search_sides", _fake_expand_search_sides)

    response = client.post("/api/v1/search/quick", json=_base_payload(str(target_date)))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) >= 1
    assert payload["meta"]["rescue"]["attempted"] is True
    assert payload["meta"]["rescue"]["winning_step"] == "pass_4_rescue_nearby"
    assert "nearby_auto" in payload["filters"]["relaxed"]
    assert payload["results"][0]["origin"] == "AGP"
    assert payload["results"][0]["destination"] == "LIS"


def test_quick_search_rescue_exhausted_keeps_empty_results(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    target_date = date.today() + timedelta(days=21)
    monkeypatch.setattr(search_api, "provider", _ProviderNeverRecovers())
    monkeypatch.setattr(search_api, "expand_search_sides", _fake_expand_search_sides)

    response = client.post("/api/v1/search/quick", json=_base_payload(str(target_date)))
    assert response.status_code == 200
    payload = response.json()

    assert payload["results"] == []
    assert payload["meta"]["rescue"]["attempted"] is True
    assert payload["meta"]["rescue"]["winning_step"] is None
    assert "rescue_mode_applied" not in payload["filters"]["warnings"]
    assert payload["meta"]["rescue"]["applied_steps"] == [
        "pass_2_rescue_budget_boost",
        "pass_3_rescue_date",
        "pass_4_rescue_nearby",
        "pass_5_rescue_time_window",
    ]


def test_quick_search_exact_success_does_not_trigger_rescue(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    target_date = date.today() + timedelta(days=21)
    monkeypatch.setattr(search_api, "provider", _ProviderExactSuccess())
    monkeypatch.setattr(search_api, "expand_search_sides", _fake_expand_search_sides)

    response = client.post("/api/v1/search/quick", json=_base_payload(str(target_date)))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) == 1
    assert payload["meta"]["rescue"]["attempted"] is False
    assert payload["meta"]["rescue"]["winning_step"] is None
    assert payload["meta"]["rescue"]["applied_steps"] == []
    assert "rescue_mode_applied" not in payload["filters"]["warnings"]
