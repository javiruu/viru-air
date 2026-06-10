"""Unit tests for quick-search shared cache model and key canonicalization (Phase 2-3)."""
import datetime as dt

import pytest

from app.services.quick_search_execution import (
    build_cache_source_hash,
    build_unit_cache_key,
    classify_cache_result,
)
from app.domain.entities import ProviderFlight, ProviderFetchResult


# ---------------------------------------------------------------------------
# Phase 2: canonicalization
# ---------------------------------------------------------------------------


class TestBuildUnitCacheKey:
    def test_same_inputs_produce_same_key(self):
        key1 = build_unit_cache_key(
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date="2026-03-11",
            provider="ryanair",
        )
        key2 = build_unit_cache_key(
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date="2026-03-11",
            provider="ryanair",
        )
        assert key1 == key2

    def test_different_origins_produce_different_keys(self):
        key1 = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        key2 = build_unit_cache_key(
            origin_iata="MAD", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        assert key1 != key2

    def test_different_dates_produce_different_keys(self):
        key1 = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        key2 = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-12", provider="ryanair",
        )
        assert key1 != key2

    def test_different_providers_produce_different_keys(self):
        key1 = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        key2 = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="duffel",
        )
        assert key1 != key2

    def test_case_and_whitespace_are_normalized(self):
        key1 = build_unit_cache_key(
            origin_iata=" agp ", destination_iata="tsf",
            travel_date="2026-03-11", provider="Ryanair",
        )
        key2 = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        assert key1 == key2

    def test_date_object_normalized_to_iso_string(self):
        key_date_obj = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date=dt.date(2026, 3, 11), provider="ryanair",
        )
        key_date_str = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        assert key_date_obj == key_date_str

    def test_inverting_origin_destination_changes_key(self):
        key1 = build_unit_cache_key(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        key2 = build_unit_cache_key(
            origin_iata="TSF", destination_iata="AGP",
            travel_date="2026-03-11", provider="ryanair",
        )
        assert key1 != key2


class TestBuildCacheSourceHash:
    def test_equivalent_inputs_produce_same_hash(self):
        h1 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        h2 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        assert h1 == h2

    def test_different_dates_produce_different_hashes(self):
        h1 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        h2 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-12", provider="ryanair",
        )
        assert h1 != h2

    def test_hash_is_stable(self):
        h = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        assert isinstance(h, str)
        assert h.startswith("qs_")
        assert len(h) == 19  # "qs_" + 16 hex chars

    def test_case_normalization_in_hash(self):
        h1 = build_cache_source_hash(
            origin_iata=" agp ", destination_iata="TSF",
            travel_date="2026-03-11", provider="Ryanair",
        )
        h2 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-03-11", provider="ryanair",
        )
        assert h1 == h2


# ---------------------------------------------------------------------------
# Phase 3: result classification
# ---------------------------------------------------------------------------


class TestClassifyCacheResult:
    def test_result_with_flights_and_no_warnings_is_ready(self):
        flights = [
            ProviderFlight(
                price=29.99, currency="EUR",
                departure_time_local="14:30",
                captured_at=dt.datetime(2026, 6, 10, 12, 0),
                source="ryanair",
            )
        ]
        category = classify_cache_result(flights=flights, warnings=[])
        assert category == "ready"

    def test_result_with_flights_and_provider_warnings_is_degraded(self):
        flights = [
            ProviderFlight(
                price=29.99, currency="EUR",
                departure_time_local="14:30",
                captured_at=dt.datetime(2026, 6, 10, 12, 0),
                source="ryanair",
            )
        ]
        category = classify_cache_result(
            flights=flights,
            warnings=["provider_timeout_partial"],
        )
        assert category == "degraded"

    def test_result_with_no_flights_is_empty(self):
        category = classify_cache_result(flights=[], warnings=[])
        assert category == "empty"

    def test_result_with_no_flights_but_warnings_is_degraded(self):
        """Empty flights + provider degradation = degraded (not empty).
        Provider degradation signals (timeout, errors) mean the provider
        may recover soon, so we cache briefly as degraded (30min) instead
        of empty (2h).
        """
        category = classify_cache_result(
            flights=[],
            warnings=["provider_error_partial", "provider_timeout_partial"],
        )
        assert category == "degraded"

    def test_degraded_detects_ryanair_specific_codes(self):
        flights = [
            ProviderFlight(
                price=49.99, currency="EUR",
                departure_time_local="10:00",
                captured_at=dt.datetime(2026, 6, 10, 12, 0),
                source="ryanair",
            )
        ]
        category = classify_cache_result(
            flights=flights,
            warnings=["ryanair_availability_failed_partial"],
        )
        assert category == "degraded"

    def test_partial_results_served_triggers_degraded(self):
        flights = [
            ProviderFlight(
                price=19.99, currency="EUR",
                departure_time_local="08:00",
                captured_at=dt.datetime(2026, 6, 10, 12, 0),
                source="ryanair",
            )
        ]
        category = classify_cache_result(
            flights=flights,
            warnings=["provider_partial_results_served"],
        )
        assert category == "degraded"
