"""Integration tests for quick-search shared cache (Fase 14).

Covers:
- Cross-user cache reuse via L2 callables
- L1→L2→provider cascade
- TTL differentiation: ready/empty/degraded
- Anti-stampede: per-key locks prevent duplicate provider calls
"""
import datetime as dt
import threading
import time
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.infrastructure.db.models import Base, QuickSearchCacheEntry, QuickSearchNegativeCacheEntry
from app.services.quick_search_cache_service import prune_expired_entries
from app.services.quick_search_execution import (
    _CACHE,
    _FETCH_LOCKS,
    _FETCH_LOCKS_LOCK,
    build_cache_source_hash,
    build_execution_plan,
    classify_cache_result,
    execute_plan,
)
from app.services.quick_search_planner import PairPlanItem


class SharedCacheIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        _CACHE.clear()
        with _FETCH_LOCKS_LOCK:
            _FETCH_LOCKS.clear()

    def _pair(self, o: str, d: str, score: float = 0.0, reason: str = "seed-seed") -> PairPlanItem:
        return PairPlanItem(
            origin_iata=o,
            destination_iata=d,
            origin_seed_iata=o,
            destination_seed_iata=d,
            origin_is_seed=True,
            destination_is_seed=True,
            origin_distance_from_seed_km=0.0,
            destination_distance_from_seed_km=0.0,
            pair_priority_score=score,
            pair_reason=reason,
        )

    def _make_flight(self, origin: str, destination: str, price: float = 29.99) -> ProviderFlight:
        return ProviderFlight(
            price=price,
            currency="EUR",
            departure_time_local="14:30",
            captured_at=dt.datetime(2026, 6, 10, 12, 0),
            source=f"{origin}-{destination}-test",
        )

    def _db(self) -> tuple[Session, Engine]:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = TestingSessionLocal()
        return session, engine

    # ------------------------------------------------------------------
    # L2 cache read-through (cross-user reuse)
    # ------------------------------------------------------------------

    def test_l2_cache_get_returns_hit_when_entry_exists(self):
        """Second execution plan reuses L2 cache populated by the first."""
        pairs = [self._pair("AGP", "TSF")]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        l2_store: dict = {}
        calls_count = {"n": 0}

        def l2_get(origin, destination, date, provider):
            key = (origin, destination, str(date), provider)
            return l2_store.get(key)

        def l2_set(origin, destination, date, provider, result):
            key = (origin, destination, str(date), provider)
            l2_store[key] = result

        def fake_fetch(origin, destination, date_str, timeout_ms):
            calls_count["n"] += 1
            flight = ProviderFlight(
                price=19.99, currency="EUR",
                departure_time_local="10:00",
                captured_at=dt.datetime(2026, 9, 1),
                source="test-l2",
            )
            return ProviderFetchResult(flights=[flight], warnings=[])

        # First call populates L2
        rows1, meta1, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=l2_get,
            shared_cache_set=l2_set,
        )
        self.assertEqual(len(rows1), 1)
        self.assertEqual(meta1["provider_calls"], 1)
        self.assertEqual(len(l2_store), 1)

        # Clear L1 to force L2 lookup on second call
        _CACHE.clear()

        # Second call should hit L2 (not provider)
        rows2, meta2, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=l2_get,
            shared_cache_set=l2_set,
        )
        self.assertEqual(len(rows2), 1)
        self.assertEqual(meta2["l2_cache_hits"], 1)
        self.assertEqual(meta2["provider_calls"], 0)
        # Provider was only called once total
        self.assertEqual(calls_count["n"], 1)

    def test_l2_cache_skipped_when_callables_are_none(self):
        """When shared_cache_get is None, fall back to L1 + provider."""
        pairs = [self._pair("AGP", "TSF")]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        calls = {"n": 0}

        def fake_fetch(origin, destination, date_str, timeout_ms):
            calls["n"] += 1
            return [self._make_flight(origin, destination)]

        rows, meta, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=None,
            shared_cache_set=None,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(meta["provider_calls"], 1)
        self.assertEqual(meta["l2_cache_hits"], 0)

    # ------------------------------------------------------------------
    # TTL differentiation
    # ------------------------------------------------------------------

    def test_l2_cache_miss_returns_fresh_provider_result(self):
        """L2 cache miss triggers provider call and populates L2."""
        pairs = [self._pair("MAD", "BCN")]
        dates = [dt.date(2026, 8, 15)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        l2_store: dict = {}
        called = {"n": 0}

        def l2_get(origin, destination, date, provider):
            key = (origin, destination, str(date), provider)
            return l2_store.get(key)

        def l2_set(origin, destination, date, provider, result):
            key = (origin, destination, str(date), provider)
            l2_store[key] = result

        def fake_fetch(origin, destination, date_str, timeout_ms):
            called["n"] += 1
            return ProviderFetchResult(
                flights=[self._make_flight(origin, destination)],
                warnings=[],
            )

        rows, meta, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=l2_get,
            shared_cache_set=l2_set,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(meta["provider_calls"], 1)
        self.assertEqual(called["n"], 1)
        # L2 should now be populated
        self.assertIn(("MAD", "BCN", "2026-08-15", "multi"), l2_store)

    # ------------------------------------------------------------------
    # Anti-stampede: per-key locks
    # ------------------------------------------------------------------

    def test_anti_stampede_prevents_duplicate_concurrent_fetches(self):
        """Two identical units in the same plan only trigger one provider call."""
        # Two pairs that share the same (origin, dest) but different reasons
        pairs = [
            self._pair("AGP", "TSF", score=0.0, reason="seed-seed"),
            self._pair("AGP", "TSF", score=1.0, reason="seed-nearby"),
        ]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=10)

        calls = {"n": 0}
        lock = threading.Lock()

        def slow_fetch(origin, destination, date_str, timeout_ms):
            time.sleep(0.05)  # simulate network latency
            with lock:
                calls["n"] += 1
            return [self._make_flight(origin, destination)]

        rows, meta, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=5000,
            fetch_flights=slow_fetch,
        )
        # Both units should return results
        self.assertEqual(len(rows), 2)
        # But provider should only be called once due to anti-stampede
        # (both units share the same key)
        self.assertEqual(calls["n"], 1)

    def test_anti_stampede_different_routes_still_fetch_independently(self):
        """Different origins should each trigger their own provider call."""
        pairs = [
            self._pair("AGP", "TSF", score=0.0, reason="seed-seed"),
            self._pair("MAD", "BCN", score=0.0, reason="seed-seed"),
        ]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=10)

        calls = {"n": 0}
        lock = threading.Lock()

        def slow_fetch(origin, destination, date_str, timeout_ms):
            with lock:
                calls["n"] += 1
            return [self._make_flight(origin, destination)]

        rows, meta, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=5000,
            fetch_flights=slow_fetch,
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(calls["n"], 2)

    # ------------------------------------------------------------------
    # L1 cache still works independently
    # ------------------------------------------------------------------

    def test_l1_cache_survives_without_l2(self):
        """Without L2 callables, L1 cache (300s) still deduplicates."""
        pairs = [self._pair("LEI", "DUB")]
        dates = [dt.date(2030, 1, 9)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        calls = {"n": 0}

        def fake_fetch(origin, destination, date_str, timeout_ms):
            calls["n"] += 1
            return [self._make_flight(origin, destination)]

        rows1, _meta1, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
        )
        rows2, meta2, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
        )
        self.assertEqual(len(rows1), 1)
        self.assertEqual(len(rows2), 1)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(meta2["l1_cache_hits"], 1)

    # ------------------------------------------------------------------
    # Result classification for TTL
    # ------------------------------------------------------------------

    def test_classify_ready_results_have_flights_and_no_warnings(self):
        flights = [self._make_flight("AGP", "TSF")]
        self.assertEqual(classify_cache_result(flights=flights, warnings=[]), "ready")

    def test_classify_degraded_results_have_flights_and_warnings(self):
        flights = [self._make_flight("AGP", "TSF")]
        self.assertEqual(
            classify_cache_result(flights=flights, warnings=["provider_timeout_partial"]),
            "degraded",
        )

    def test_classify_empty_results_without_warnings_remain_empty(self):
        self.assertEqual(classify_cache_result(flights=[], warnings=[]), "empty")

    def test_classify_empty_with_degradation_is_degraded(self):
        self.assertEqual(
            classify_cache_result(flights=[], warnings=["provider_error_partial"]),
            "degraded",
        )

    # ------------------------------------------------------------------
    # Cache source hash stability
    # ------------------------------------------------------------------

    def test_source_hash_consistent_for_equivalent_inputs(self):
        h1 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-12-25", provider="ryanair",
        )
        h2 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-12-25", provider="ryanair",
        )
        self.assertEqual(h1, h2)
        self.assertTrue(h1.startswith("qs_"))
        self.assertEqual(len(h1), 19)

    def test_source_hash_differs_for_different_providers(self):
        h1 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-12-25", provider="ryanair",
        )
        h2 = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-12-25", provider="duffel",
        )
        self.assertNotEqual(h1, h2)

    def test_source_hash_differs_for_different_currencies(self):
        """Different currencies must produce different hashes to prevent cross-currency cache poisoning."""
        h_eur = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-12-25", provider="ryanair",
            currency="EUR",
        )
        h_usd = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-12-25", provider="ryanair",
            currency="USD",
        )
        h_gbp = build_cache_source_hash(
            origin_iata="AGP", destination_iata="TSF",
            travel_date="2026-12-25", provider="ryanair",
            currency="GBP",
        )
        self.assertNotEqual(h_eur, h_usd)
        self.assertNotEqual(h_eur, h_gbp)
        self.assertNotEqual(h_usd, h_gbp)

    # ------------------------------------------------------------------
    # Nearby/flex: cache works for expanded units
    # ------------------------------------------------------------------

    def test_l2_cache_works_for_nearby_pairs(self):
        """Nearby pairs use the same L2 key space as seed-seed."""
        pairs = [
            self._pair("AGP", "TSF", score=0.0, reason="seed-seed"),
            self._pair("AGP", "VCE", score=100.0, reason="seed-nearby"),
        ]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=10)

        l2_store: dict = {}

        def l2_get(origin, destination, date, provider):
            return l2_store.get((origin, destination, str(date), provider))

        def l2_set(origin, destination, date, provider, result):
            l2_store[(origin, destination, str(date), provider)] = result

        calls = {"n": 0}

        def fake_fetch(origin, destination, date_str, timeout_ms):
            calls["n"] += 1
            return ProviderFetchResult(
                flights=[self._make_flight(origin, destination)],
                warnings=[],
            )

        rows1, meta1, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=l2_get,
            shared_cache_set=l2_set,
        )
        self.assertEqual(len(rows1), 2)
        # Two distinct pairs → 2 provider calls
        self.assertEqual(meta1["provider_calls"], 2)
        self.assertEqual(len(l2_store), 2)

        # Clear L1 to force L2 lookup on re-run
        _CACHE.clear()

        # Re-run the same plan — both pairs should hit L2
        rows2, meta2, _ = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=l2_get,
            shared_cache_set=l2_set,
        )
        self.assertEqual(len(rows2), 2)
        self.assertEqual(meta2["l2_cache_hits"], 2)
        self.assertEqual(meta2["provider_calls"], 0)

    # ------------------------------------------------------------------
    # Warnings propagation through cache
    # ------------------------------------------------------------------

    def test_warnings_survive_through_cache_roundtrip(self):
        """Warnings from provider result should be preserved in L2."""
        pairs = [self._pair("AGP", "TSF")]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        l2_store: dict = {}

        def l2_get(origin, destination, date, provider):
            return l2_store.get((origin, destination, str(date), provider))

        def l2_set(origin, destination, date, provider, result):
            l2_store[(origin, destination, str(date), provider)] = result

        def fake_fetch(origin, destination, date_str, timeout_ms):
            return ProviderFetchResult(
                flights=[self._make_flight(origin, destination)],
                warnings=["provider_timeout_partial"],
            )

        rows1, meta1, warnings1 = execute_plan(
            plan, concurrency_limit=2, timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=l2_get,
            shared_cache_set=l2_set,
        )
        self.assertIn("provider_timeout_partial", warnings1)

        # The cached result should still have the warning
        cached = l2_store.get(("AGP", "TSF", "2026-12-25", "multi"))
        self.assertIsNotNone(cached)
        self.assertIn("provider_timeout_partial", cached.warnings)

    def test_negative_cache_hit_skips_provider_call(self):
        pairs = [self._pair("AGP", "TSF")]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        calls = {"n": 0}

        def fake_fetch(origin, destination, date_str, timeout_ms):
            calls["n"] += 1
            return ProviderFetchResult(
                flights=[self._make_flight(origin, destination)],
                warnings=[],
            )

        def negative_get(origin, destination, date, provider):
            return ProviderFetchResult(flights=[], warnings=[])

        rows, meta, warnings = execute_plan(
            plan,
            concurrency_limit=2,
            timeout_ms=3000,
            fetch_flights=fake_fetch,
            negative_cache_get=negative_get,
        )

        self.assertEqual(rows, [])
        self.assertEqual(warnings, [])
        self.assertEqual(calls["n"], 0)
        self.assertEqual(meta["negative_cache_hits"], 1)
        self.assertEqual(meta["provider_calls"], 0)

    def test_negative_cache_provider_error_backoff_skips_provider_and_preserves_warning(self):
        pairs = [self._pair("AGP", "TSF")]
        dates = [dt.date(2026, 12, 25)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        calls = {"n": 0}

        def fake_fetch(origin, destination, date_str, timeout_ms):
            calls["n"] += 1
            return ProviderFetchResult(flights=[self._make_flight(origin, destination)], warnings=[])

        def negative_get(origin, destination, date, provider):
            return ProviderFetchResult(flights=[], warnings=["provider_timeout_partial"])

        rows, meta, warnings = execute_plan(
            plan,
            concurrency_limit=2,
            timeout_ms=3000,
            fetch_flights=fake_fetch,
            negative_cache_get=negative_get,
        )

        self.assertEqual(rows, [])
        self.assertEqual(calls["n"], 0)
        self.assertEqual(meta["negative_cache_hits"], 1)
        self.assertIn("provider_timeout_partial", warnings)

    def test_pruning_removes_only_expired_positive_and_negative_entries(self):
        db, engine = self._db()
        now = utc_now_naive()
        try:
            db.add_all(
                [
                    QuickSearchCacheEntry(
                        origin_iata="AGP",
                        destination_iata="TSF",
                        travel_date=dt.date(2026, 12, 25),
                        provider="multi",
                        status="ready",
                        ttl_seconds=60,
                        expires_at_utc=now - dt.timedelta(seconds=1),
                        captured_at_utc=now - dt.timedelta(minutes=2),
                        last_accessed_at_utc=now - dt.timedelta(minutes=2),
                        payload_json='{"flights":[]}',
                        warnings_json="[]",
                        source_hash="qs_expired_positive",
                    ),
                    QuickSearchCacheEntry(
                        origin_iata="AGP",
                        destination_iata="DUB",
                        travel_date=dt.date(2026, 12, 25),
                        provider="multi",
                        status="ready",
                        ttl_seconds=3600,
                        expires_at_utc=now + dt.timedelta(hours=1),
                        captured_at_utc=now,
                        last_accessed_at_utc=now,
                        payload_json='{"flights":[]}',
                        warnings_json="[]",
                        source_hash="qs_fresh_positive",
                    ),
                    QuickSearchNegativeCacheEntry(
                        negative_fingerprint="qsn_expired",
                        scope="provider_unit",
                        reason="no_availability",
                        provider="multi",
                        canonical_request_json="{}",
                        observed_at=now - dt.timedelta(minutes=2),
                        expires_at=now - dt.timedelta(seconds=1),
                        freshness_status="negative_fresh",
                    ),
                    QuickSearchNegativeCacheEntry(
                        negative_fingerprint="qsn_fresh",
                        scope="provider_unit",
                        reason="provider_timeout",
                        provider="multi",
                        canonical_request_json="{}",
                        observed_at=now,
                        expires_at=now + dt.timedelta(minutes=10),
                        freshness_status="provider_error_fresh",
                    ),
                ]
            )
            db.commit()

            deleted = prune_expired_entries(db, batch_size=50)

            positive_hashes = set(db.scalars(select(QuickSearchCacheEntry.source_hash)).all())
            negative_hashes = set(db.scalars(select(QuickSearchNegativeCacheEntry.negative_fingerprint)).all())
            self.assertEqual(deleted, 2)
            self.assertEqual(positive_hashes, {"qs_fresh_positive"})
            self.assertEqual(negative_hashes, {"qsn_fresh"})
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
