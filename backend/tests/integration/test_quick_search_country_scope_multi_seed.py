from __future__ import annotations

from datetime import date, timedelta

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.infrastructure.airports_catalog import ExpandedAirportCandidate
from app.services.quick_search_execution import _CACHE
from app.services.quick_search_expansion import SideExpansionResult, SideExpansionSummary


def _build_side_result(side: str, seed_iata: str, include_nearby: bool, radius_km: int, max_candidates: int) -> SideExpansionResult:
    candidates = [
        ExpandedAirportCandidate(
            seed_iata=seed_iata,
            expanded_iata=seed_iata,
            is_seed=True,
            distance_km=0.0,
            candidate_reason="seed",
            source_of_expansion="test-country-scope",
        )
    ]
    if include_nearby:
        nearby_code = "BLQ" if side == "origin" else "GRO"
        candidates.append(
            ExpandedAirportCandidate(
                seed_iata=seed_iata,
                expanded_iata=nearby_code,
                is_seed=False,
                distance_km=31.0,
                candidate_reason="nearby",
                source_of_expansion="test-country-scope",
            )
        )

    limited = candidates[: max(1, max_candidates)]
    return SideExpansionResult(
        side=side,
        candidates=limited,
        summary=SideExpansionSummary(
            side=side,
            seed_iata=seed_iata,
            include_nearby_applied=include_nearby,
            radius_km_effective=radius_km,
            max_candidates_effective=max(1, max_candidates),
            exclusions_applied=[],
            total_candidates_before_limit=len(candidates),
            total_candidates_after_limit=len(limited),
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
        _build_side_result("origin", origin_seed_iata, include_nearby_origins, origin_radius_km, origin_max_candidates),
        _build_side_result("destination", destination_seed_iata, include_nearby_destinations, destination_radius_km, destination_max_candidates),
    )


class _ProviderOnlySecondSeedPair:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        del travel_date, timeout_ms
        if origin == "FCO" and destination == "MAD":
            return ProviderFetchResult(
                flights=[
                    ProviderFlight(
                        price=62.0,
                        currency="EUR",
                        departure_time_local="12:00",
                        captured_at=utc_now_naive(),
                        source="fake-country-scope",
                    )
                ],
                warnings=[],
            )
        return ProviderFetchResult(flights=[], warnings=[])


class _ProviderDateRescueSecondSeed:
    def __init__(self, target: date) -> None:
        self._target = target

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        del timeout_ms
        query_date = date.fromisoformat(travel_date)
        if origin == "FCO" and destination == "MAD" and query_date == self._target + timedelta(days=1):
            return ProviderFetchResult(
                flights=[
                    ProviderFlight(
                        price=58.5,
                        currency="EUR",
                        departure_time_local="10:10",
                        captured_at=utc_now_naive(),
                        source="fake-country-rescue",
                    )
                ],
                warnings=["ryanair_availability_failed_partial"],
            )
        return ProviderFetchResult(flights=[], warnings=["ryanair_availability_failed_partial"])


class _ProviderAlwaysEmptyPartial:
    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        del origin, destination, travel_date, timeout_ms
        return ProviderFetchResult(flights=[], warnings=["ryanair_availability_failed_partial"])


def _payload(travel_date_iso: str) -> dict:
    return {
        "origin": {
            "seed_iata": "AHO",
            "seed_iata_list": ["AHO", "FCO", "MXP"],
            "include_nearby": False,
            "radius_km": 150,
            "max_candidates": 6,
        },
        "destination": {
            "seed_iata": "VIT",
            "seed_iata_list": ["VIT", "MAD", "BCN"],
            "include_nearby": False,
            "radius_km": 150,
            "max_candidates": 6,
        },
        "travel": {"date": travel_date_iso, "flex_before": 0, "flex_after": 0},
        "constraints": {
            "departure_window": {"after": "07:00", "before": "22:00"},
            "strict_filters": True,
            "include_stops": False,
            "max_stops": 0,
            "soft_filters_weight": 0.6,
        },
    }


def test_country_scope_multi_seed_returns_results_from_secondary_seed(client, monkeypatch) -> None:
    _CACHE.clear()
    travel_date_iso = str(date.today() + timedelta(days=30))
    monkeypatch.setattr(search_api, "provider", _ProviderOnlySecondSeedPair())
    monkeypatch.setattr(search_api, "expand_search_sides", _fake_expand_search_sides)

    response = client.post("/api/v1/search/quick", json=_payload(travel_date_iso))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) >= 1
    assert payload["results"][0]["origin"] == "FCO"
    assert payload["results"][0]["destination"] == "MAD"
    assert payload["meta"]["rescue"]["attempted"] is False
    assert payload["query"]["origin"]["seed_iata_list"][0] == "FCO"
    assert "MAD" in payload["query"]["destination"]["seed_iata_list"]
    assert any(item["code"] == "country_scope_multi_seed_applied" for item in payload["meta"]["warnings_structured"])


def test_country_scope_multi_seed_rescue_finds_results(client, monkeypatch) -> None:
    _CACHE.clear()
    target = date.today() + timedelta(days=30)
    monkeypatch.setattr(search_api, "provider", _ProviderDateRescueSecondSeed(target))
    monkeypatch.setattr(search_api, "expand_search_sides", _fake_expand_search_sides)

    response = client.post("/api/v1/search/quick", json=_payload(str(target)))
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) >= 1
    assert payload["meta"]["rescue"]["attempted"] is True
    assert payload["meta"]["rescue"]["winning_step"] == "pass_2_rescue_date"
    assert "date_flex_auto" in payload["filters"]["relaxed"]


def test_country_scope_multi_seed_exhausted_keeps_empty_with_metadata(client, monkeypatch) -> None:
    _CACHE.clear()
    target = date.today() + timedelta(days=30)
    monkeypatch.setattr(search_api, "provider", _ProviderAlwaysEmptyPartial())
    monkeypatch.setattr(search_api, "expand_search_sides", _fake_expand_search_sides)

    response = client.post("/api/v1/search/quick", json=_payload(str(target)))
    assert response.status_code == 200
    payload = response.json()

    assert payload["results"] == []
    assert payload["meta"]["rescue"]["attempted"] is True
    assert payload["meta"]["rescue"]["winning_step"] is None
    assert "rescue_mode_applied" in payload["filters"]["warnings"]
    assert any(item["code"] == "country_scope_multi_seed_applied" for item in payload["meta"]["warnings_structured"])
