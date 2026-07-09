import datetime as dt
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

try:
    from app.api.v1.search import (
        _CALENDAR_HINTS_CACHE,
        QuickSearchCalendarHintsIn,
        QuickSearchSaveResultIn,
        quick_search,
        quick_search_calendar_hints,
        save_result,
    )
    from app.domain.entities import ProviderFetchResult, ProviderFlight
    from app.infrastructure.db.models import Base, PriceSnapshot, RevalidationJob
    from app.infrastructure.providers.orchestrator import FlightSearchOrchestrator
    from app.services.quick_search_ai_preference import QuickSearchAiPreferenceResult
    from app.services.quick_search_execution import _CACHE
    from app.services.watchlist_revalidation import process_due_route_revalidation_jobs
except Exception:  # pragma: no cover
    _CALENDAR_HINTS_CACHE = None
    QuickSearchCalendarHintsIn = None
    QuickSearchSaveResultIn = None
    quick_search = None
    quick_search_calendar_hints = None
    save_result = None
    ProviderFetchResult = None
    ProviderFlight = None
    Base = None
    PriceSnapshot = None
    RevalidationJob = None
    FlightSearchOrchestrator = None
    QuickSearchAiPreferenceResult = None
    _CACHE = None
    process_due_route_revalidation_jobs = None


def _flight(price: float, dep: str, source: str = "test-provider", currency: str = "EUR") -> ProviderFlight:
    return ProviderFlight(
        price=price,
        currency=currency,
        departure_time_local=dep,
        captured_at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
        source=source,
    )


def _db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, TestingSessionLocal, TestingSessionLocal()


class _FakeProvider:
    def __init__(self, *, return_value=None, side_effect=None, provider_ids=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self._provider_ids = provider_ids or ["ryanair", "wizzair"]
        self.get_flights_calls = 0

    def get_flights(self, origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
        self.get_flights_calls += 1
        if self.side_effect is not None:
            return self.side_effect(origin, destination, date, timeout_ms, currency)
        return self.return_value

    def provider_ids(self) -> list[str]:
        return list(self._provider_ids)


def _patch_request_provider(*, return_value=None, side_effect=None, provider_ids=None):
    fake_provider = _FakeProvider(return_value=return_value, side_effect=side_effect, provider_ids=provider_ids)
    return patch("app.api.v1.search._build_request_provider", return_value=fake_provider)


class _RouteRefreshProvider:
    def get_flights(self, origin: str, destination: str, travel_date: str):
        return [_flight(63.0, "10:15", source="route-refresh-test")]

    def provider_ids(self) -> list[str]:
        return ["route-refresh-test"]


@unittest.skipIf(
    quick_search is None
    or quick_search_calendar_hints is None
    or QuickSearchCalendarHintsIn is None
    or QuickSearchSaveResultIn is None
    or save_result is None
    or ProviderFlight is None
    or PriceSnapshot is None
    or RevalidationJob is None
    or QuickSearchAiPreferenceResult is None
    or process_due_route_revalidation_jobs is None,
    "fastapi app deps not available",
)
class QuickSearchE2ERegressionTests(unittest.TestCase):
    def setUp(self):
        if _CACHE is not None:
            _CACHE.clear()
        if _CALENDAR_HINTS_CACHE is not None:
            _CALENDAR_HINTS_CACHE.clear()

    def _payload(self, **overrides):
        payload = {
            "origin": {"seed_iata": "LEI", "include_nearby": False, "radius_km": 250, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 250, "max_candidates": 6},
            "travel": {"date": "2026-06-14", "flex_before": 0, "flex_after": 0},
            "constraints": {"strict_filters": True},
            "execution": {"max_pairs": 12, "max_requests": 24, "timeout_ms": 3000, "concurrency_limit": 4},
        }
        payload.update(overrides)
        return payload

    def _call_quick_search(self, payload, debug=True, page=None, page_size=None, db=None):
        return quick_search(
            payload=payload,
            origin_iata=None,
            destination_iata=None,
            travel_date=None,
            radius_km=None,
            include_stops=None,
            include_nearby_origins=None,
            include_nearby_destinations=None,
            depart_after=None,
            depart_before=None,
            max_stops=None,
            exclude_origins=None,
            exclude_destinations=None,
            strict_filters=None,
            soft_filters_weight=None,
            flex_days_before=None,
            flex_days_after=None,
            page=page,
            page_size=page_size,
            debug=debug,
            db=db,
        )

    def test_seed_only_base_flow(self):
        payload = self._payload()
        with _patch_request_provider(return_value=[_flight(55, "10:00")]):
            result = self._call_quick_search(payload)

        self.assertEqual(result["meta"]["query_trace_id"][:3], "qs_")
        self.assertEqual(len(result["results"]), 1)
        first = result["results"][0]
        self.assertEqual(first["origin"], "LEI")
        self.assertEqual(first["destination"], "DUB")
        self.assertEqual(first["result_id"], "LEI-DUB-2026-06-14-0")
        self.assertEqual(first["price_total"], 55)
        self.assertIsInstance(first["duration_total_min"], int)
        self.assertGreater(first["duration_total_min"], 0)
        self.assertIsInstance(first["freshness_ts"], str)
        self.assertEqual(first["freshness"]["status"], "fresh")
        self.assertFalse(first["freshness"]["requires_revalidation"])
        self.assertEqual(first["freshness"]["validation_status"], "revalidated")
        self.assertEqual(first["ranking_score"], first["score"]["final_score"])
        self.assertFalse(first["stale_data"])
        self.assertEqual(first["itinerary_type"], "direct")
        self.assertEqual(first["legs"], [])
        self.assertFalse(result["meta"]["search_cache"]["exact_hit"])
        self.assertIsNotNone(result["meta"]["search_cache"]["freshness"])
        self.assertFalse(result["meta"]["search_cache"]["requires_revalidation"])

    def test_origin_nearby_expansion_is_real(self):
        payload = self._payload(origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 4})

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            if origin == "LEI":
                return [_flight(62, "09:30")]
            if origin == "AGP":
                return [_flight(58, "09:45")]
            return []

        with _patch_request_provider(side_effect=fake_fetch):
            result = self._call_quick_search(payload)

        expanded_origins = result["query"]["expanded_origins"]
        self.assertTrue(any(item["expanded_iata"] == "AGP" for item in expanded_origins))
        planned_pairs = result["meta"]["planned_pairs"]
        self.assertTrue(any(item["origin_iata"] == "AGP" for item in planned_pairs))

    def test_both_nearby_builds_cross_pairs(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3},
            destination={"seed_iata": "DUB", "include_nearby": True, "radius_km": 300, "max_candidates": 3},
            execution={"max_pairs": 8, "max_requests": 8, "timeout_ms": 3000, "concurrency_limit": 2},
        )

        with _patch_request_provider(return_value=[_flight(70, "11:00")]):
            result = self._call_quick_search(payload)

        categories = {item["pair_reason"] for item in result["meta"]["planned_pairs"]}
        self.assertIn("seed-seed", categories)
        self.assertTrue(any(cat in categories for cat in {"seed-nearby", "nearby-seed", "nearby-nearby"}))

    def test_ranking_keeps_seed_reasonable_priority(self):
        payload = self._payload(origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3})

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            if origin == "LEI":
                return [_flight(60, "10:00")]
            if origin == "AGP":
                return [_flight(58, "10:00")]
            return []

        with _patch_request_provider(side_effect=fake_fetch):
            result = self._call_quick_search(payload)

        self.assertGreaterEqual(len(result["results"]), 1)
        top = result["results"][0]
        self.assertEqual(top["origin"], "LEI")
        self.assertEqual(top["pair_category"], "seed-seed")

    def test_budget_degradation_and_warnings(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 4},
            destination={"seed_iata": "DUB", "include_nearby": True, "radius_km": 300, "max_candidates": 4},
            travel={"date": "2026-06-14", "flex_before": 1, "flex_after": 1},
            execution={"max_pairs": 10, "max_requests": 2, "timeout_ms": 3000, "concurrency_limit": 2},
        )
        with _patch_request_provider(return_value=[_flight(90, "12:00")]):
            result = self._call_quick_search(payload)

        warning_codes = {w["code"] for w in result["meta"]["warnings_structured"]}
        self.assertIn("max_pairs_truncated", warning_codes)
        self.assertFalse(result["meta"]["execution"]["truncated_by_max_requests"])
        self.assertTrue(result["meta"]["truncation_signals"]["pair_cap"])
        self.assertIn("execution_budget", result["meta"])

    def test_timeout_partial_does_not_break_whole_search(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3},
            execution={"max_pairs": 6, "max_requests": 6, "timeout_ms": 1500, "concurrency_limit": 2},
        )

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            if origin == "AGP":
                raise TimeoutError("provider timeout")
            return [_flight(72, "13:00")]

        with _patch_request_provider(side_effect=fake_fetch):
            result = self._call_quick_search(payload)

        warning_codes = {w["code"] for w in result["meta"]["warnings_structured"]}
        self.assertIn("provider_timeout_partial", warning_codes)
        self.assertGreaterEqual(len(result["results"]), 1)

    def test_pagination_meta_and_page_window(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3},
            destination={"seed_iata": "DUB", "include_nearby": True, "radius_km": 300, "max_candidates": 3},
            execution={"max_pairs": 12, "max_requests": 48, "timeout_ms": 3000, "concurrency_limit": 2},
            pagination={"page": 2, "page_size": 2},
        )
        with _patch_request_provider(return_value=[_flight(60, "10:00")]):
            result = self._call_quick_search(payload)
        pagination = result["meta"]["pagination"]
        self.assertEqual(pagination["page"], 2)
        self.assertEqual(pagination["page_size"], 2)
        self.assertGreaterEqual(pagination["total_results"], len(result["results"]))
        self.assertGreaterEqual(pagination["total_pages"], 1)
        self.assertLessEqual(len(result["results"]), 2)

    def test_pagination_out_of_range_clamps_to_last_page(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3},
            destination={"seed_iata": "DUB", "include_nearby": True, "radius_km": 300, "max_candidates": 3},
            execution={"max_pairs": 12, "max_requests": 48, "timeout_ms": 3000, "concurrency_limit": 2},
            pagination={"page": 999, "page_size": 3},
        )
        with _patch_request_provider(return_value=[_flight(65, "11:00")]):
            result = self._call_quick_search(payload)
        pagination = result["meta"]["pagination"]
        self.assertEqual(pagination["page"], pagination["total_pages"])
        self.assertGreaterEqual(pagination["total_pages"], 1)

    def test_provider_warning_passthrough_and_alias_normalization(self):
        payload = self._payload()

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            return ProviderFetchResult(
                flights=[_flight(77, "14:20", source="duffel-offers")],
                warnings=[
                    "provider_timeout_parcial",
                    "provider_timeout_parcial",
                    "ryanair_fares_failed_partial",
                ],
            )

        with _patch_request_provider(side_effect=fake_fetch):
            result = self._call_quick_search(payload)

        codes = [item["code"] for item in result["meta"]["warnings_structured"]]
        self.assertIn("provider_timeout_partial", codes)
        self.assertIn("ryanair_fares_failed_partial", codes)
        self.assertEqual(codes.count("provider_timeout_partial"), 1)
        self.assertIn("provider_timeout_partial", result["filters"]["warnings"])

    def test_partial_provider_failures_keep_results_from_other_pairs(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3},
            destination={"seed_iata": "DUB", "include_nearby": True, "radius_km": 300, "max_candidates": 3},
            execution={"max_pairs": 8, "max_requests": 16, "timeout_ms": 1500, "concurrency_limit": 2},
        )

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            if origin == "AGP":
                raise TimeoutError("provider timeout")
            return [_flight(91, "07:40", source="ryanair-public-fares")]

        with _patch_request_provider(side_effect=fake_fetch):
            result = self._call_quick_search(payload)

        self.assertGreaterEqual(len(result["results"]), 1)
        warning_codes = {w["code"] for w in result["meta"]["warnings_structured"]}
        self.assertIn("provider_timeout_partial", warning_codes)
        self.assertIn("provider_error_partial", warning_codes)
        self.assertGreater(result["meta"]["pipeline_counters"]["provider_failures_count"], 0)

    def test_single_pair_preserves_multi_currency_multi_source_offers(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            destination={"seed_iata": "DUB", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            execution={"max_pairs": 1, "max_requests": 1, "timeout_ms": 3000, "concurrency_limit": 1},
        )

        with _patch_request_provider(
            return_value=[
                _flight(120, "10:15", source="ryanair-public-fares", currency="EUR"),
                _flight(120, "10:15", source="duffel-offers", currency="USD"),
            ],
        ):
            result = self._call_quick_search(payload)

        self.assertEqual(len(result["results"]), 2)
        currencies = {item["currency"] for item in result["results"]}
        sources = {item["source"] for item in result["results"]}
        self.assertEqual(currencies, {"EUR", "USD"})
        self.assertEqual(sources, {"ryanair-public-fares", "duffel-offers"})

    def test_second_identical_search_uses_cache_and_reduces_provider_calls(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            destination={"seed_iata": "DUB", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            execution={"max_pairs": 1, "max_requests": 1, "timeout_ms": 3000, "concurrency_limit": 1},
        )
        calls = {"count": 0}

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            calls["count"] += 1
            return [_flight(66, "16:10", source="duffel-offers")]

        with _patch_request_provider(side_effect=fake_fetch):
            first = self._call_quick_search(payload)
            second = self._call_quick_search(payload)

        self.assertEqual(calls["count"], 1)
        self.assertEqual(first["meta"]["execution"]["cache_hits"], 0)
        self.assertGreaterEqual(second["meta"]["execution"]["cache_hits"], 1)
        self.assertEqual(first["results"][0]["price_total"], second["results"][0]["price_total"])

    def test_calendar_hints_uses_shared_fare_memory_callbacks_when_enabled(self):
        payload = QuickSearchCalendarHintsIn(
            origin_iata="LEI",
            destination_iata="DUB",
            month="2026-06",
            aggregation_mode="fixed_route",
        )
        engine, testing_session_local, db = _db_session()
        execute_plan_calls = []

        def fake_execute_plan(*args, **kwargs):
            execute_plan_calls.append(kwargs)
            return (
                [("LEI", "DUB", dt.date(2026, 6, 14), _flight(52, "08:30"))],
                {
                    "provider_calls": 0,
                    "cache_hits": 1,
                    "cache_misses": 0,
                    "l1_cache_hits": 0,
                    "l2_cache_hits": 1,
                    "negative_cache_hits": 0,
                    "provider_failures": 0,
                    "timed_out_units_count": 0,
                },
                [],
            )

        try:
            with (
                patch("app.api.v1.search.QUICK_SEARCH_SHARED_CACHE_ENABLED", True),
                patch("app.api.v1.search.FARE_MEMORY_NEGATIVE_CACHE_ENABLED", True),
                patch("app.api.v1.search.SessionLocal", testing_session_local),
                patch("app.api.v1.search.execute_plan", side_effect=fake_execute_plan),
                _patch_request_provider(return_value=[]),
            ):
                result = quick_search_calendar_hints(payload=payload, db=db)

            self.assertEqual(len(execute_plan_calls), 1)
            call_kwargs = execute_plan_calls[0]
            self.assertIsNotNone(call_kwargs["shared_cache_get"])
            self.assertIsNotNone(call_kwargs["shared_cache_set"])
            self.assertIsNotNone(call_kwargs["negative_cache_get"])
            self.assertIsNotNone(call_kwargs["negative_cache_set"])
            self.assertEqual(result["meta"]["execution"]["cache_hits"], 1)
            self.assertEqual(result["meta"]["execution"]["l2_cache_hits"], 1)
            self.assertEqual(result["meta"]["execution"]["provider_calls"], 0)
        finally:
            db.close()
            engine.dispose()

    def test_save_result_seeds_watchlist_snapshot_from_observed_price(self):
        engine, _testing_session_local, db = _db_session()
        current_user = type("CurrentUser", (), {"id": "user-quick-save"})()
        first_payload = QuickSearchSaveResultIn(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 14),
            price_total=52.5,
            currency="usd",
        )
        second_payload = QuickSearchSaveResultIn(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 14),
            price_total=49.0,
            currency="EUR",
            freshness_status="fresh",
            requires_revalidation=False,
            validation_status="revalidated",
        )
        stale_payload = QuickSearchSaveResultIn(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 14),
            price_total=47.0,
            currency="EUR",
            freshness_status="warm",
            requires_revalidation=False,
            validation_status="seen",
        )

        try:
            created = save_result(
                payload=first_payload,
                idempotency_key=None,
                db=db,
                current_user=current_user,
            )
            existing = save_result(
                payload=second_payload,
                idempotency_key=None,
                db=db,
                current_user=current_user,
            )
            idempotent = save_result(
                payload=second_payload,
                idempotency_key="save-result-price-observed",
                db=db,
                current_user=current_user,
            )
            replayed = save_result(
                payload=second_payload,
                idempotency_key="save-result-price-observed",
                db=db,
                current_user=current_user,
            )
            with self.assertLogs("app.quick_search.save_result", level="INFO") as logs:
                stale_saved = save_result(
                    payload=stale_payload,
                    idempotency_key=None,
                    db=db,
                    current_user=current_user,
                )
            snapshots_before_worker = db.scalars(
                select(PriceSnapshot)
                .where(PriceSnapshot.watch_id == created["watch_id"])
                .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
            ).all()
            jobs_before_worker = db.scalars(
                select(RevalidationJob).where(
                    RevalidationJob.target_fingerprint == "route:LEI:DUB:2026-06-14",
                )
            ).all()
            worker_report = process_due_route_revalidation_jobs(
                _testing_session_local,
                max_jobs=1,
                provider_client=_RouteRefreshProvider(),
            )
            db.expire_all()
            snapshots_after_worker = db.scalars(
                select(PriceSnapshot)
                .where(PriceSnapshot.watch_id == created["watch_id"])
                .order_by(PriceSnapshot.captured_at_utc.asc(), PriceSnapshot.id.asc())
            ).all()
            jobs_after_worker = db.scalars(
                select(RevalidationJob).where(
                    RevalidationJob.target_fingerprint == "route:LEI:DUB:2026-06-14",
                )
            ).all()

            self.assertEqual(created["created_or_existing"], "created")
            self.assertEqual(existing["created_or_existing"], "existing")
            self.assertEqual(existing["watch_id"], created["watch_id"])
            self.assertEqual(stale_saved["watch_id"], created["watch_id"])
            self.assertEqual(idempotent, replayed)
            self.assertIn("quick_search_save_result_revalidation_enqueued", "\n".join(logs.output))
            self.assertIn('"created": true', "\n".join(logs.output))
            self.assertEqual(len(snapshots_before_worker), 3)
            self.assertEqual(float(snapshots_before_worker[0].raw_price), 52.5)
            self.assertEqual(snapshots_before_worker[0].raw_currency, "USD")
            self.assertEqual(snapshots_before_worker[0].provider, "quick-search")
            self.assertFalse(snapshots_before_worker[0].is_stale)
            self.assertEqual(float(snapshots_before_worker[1].raw_price), 49.0)
            self.assertEqual(float(snapshots_before_worker[2].raw_price), 49.0)
            self.assertEqual(len(jobs_before_worker), 1)
            self.assertEqual(jobs_before_worker[0].job_type, "manual")
            self.assertEqual(jobs_before_worker[0].target_type, "route")
            self.assertEqual(jobs_before_worker[0].provider, "multi")
            self.assertEqual(worker_report["processed_job_count"], 1)
            self.assertEqual(worker_report["refreshed_job_count"], 1)
            self.assertEqual(len(snapshots_after_worker), 4)
            refreshed_snapshots = [
                snapshot
                for snapshot in snapshots_after_worker
                if snapshot.provider == "route-refresh-test"
            ]
            self.assertEqual(len(refreshed_snapshots), 1)
            self.assertEqual(float(refreshed_snapshots[0].raw_price), 63.0)
            self.assertEqual(len(jobs_after_worker), 1)
            self.assertEqual(jobs_after_worker[0].status, "done")
        finally:
            db.close()
            engine.dispose()

    def test_exact_search_cache_hit_returns_cached_payload_without_provider_call(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            destination={"seed_iata": "DUB", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            execution={"max_pairs": 1, "max_requests": 1, "timeout_ms": 3000, "concurrency_limit": 1},
        )
        cached_entry = type(
            "Entry",
            (),
            {
                "payload_json": '{"meta":{"query_signature":"qsig_cached","execution":{"cache_hits":0}},"results":[{"result_id":"cached-1","price_total":44}]}',
            },
        )()

        engine, testing_session_local, db = _db_session()
        fake_provider = _FakeProvider(return_value=[])
        try:
            with (
                patch("app.api.v1.search.QUICK_SEARCH_SHARED_CACHE_ENABLED", True),
                patch("app.api.v1.search.SessionLocal", testing_session_local),
                patch("app.api.v1.search.get_exact_search_cache_entry", return_value=cached_entry),
                patch(
                    "app.api.v1.search.build_effective_freshness",
                    return_value={
                        "status": "fresh",
                        "observed_at": "2026-06-15T10:00:00Z",
                        "expires_at": "2026-06-15T11:00:00Z",
                        "age_seconds": 30,
                        "confidence_score": 0.95,
                        "source": "provider_cache",
                        "requires_revalidation": False,
                        "validation_status": "revalidated",
                    },
                ),
                patch("app.api.v1.search._build_request_provider", return_value=fake_provider),
            ):
                result = self._call_quick_search(payload, db=db)

            self.assertEqual(fake_provider.get_flights_calls, 0)
            self.assertEqual(result["results"][0]["price_total"], 44)
            self.assertTrue(result["meta"]["search_cache"]["exact_hit"])
            self.assertTrue(result["meta"]["execution"]["exact_search_cache_hit"])
            self.assertEqual(result["meta"]["search_cache"]["freshness"]["status"], "fresh")
            self.assertEqual(result["meta"]["pipeline_counters"]["cache_hit_rate"], 1.0)
            self.assertEqual(result["meta"]["pipeline_counters"]["provider_calls_avoided"], 1)
        finally:
            db.close()
            engine.dispose()

    def test_exact_search_cache_miss_persists_final_payload(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            destination={"seed_iata": "DUB", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            execution={"max_pairs": 1, "max_requests": 1, "timeout_ms": 3000, "concurrency_limit": 1},
        )

        engine, testing_session_local, db = _db_session()
        try:
            with (
                patch("app.api.v1.search.QUICK_SEARCH_SHARED_CACHE_ENABLED", True),
                patch("app.api.v1.search.SessionLocal", testing_session_local),
                patch("app.api.v1.search.get_exact_search_cache_entry", return_value=None),
                patch("app.api.v1.search.set_exact_search_cache_entry") as set_exact_cache,
                patch(
                    "app.api.v1.search.build_effective_freshness",
                    return_value={
                        "status": "fresh",
                        "observed_at": "2026-06-15T10:00:00Z",
                        "expires_at": "2026-06-15T11:00:00Z",
                        "age_seconds": 30,
                        "confidence_score": 0.95,
                        "source": "provider_cache",
                        "requires_revalidation": False,
                        "validation_status": "revalidated",
                    },
                ),
                _patch_request_provider(return_value=[_flight(55, "10:00")]),
            ):
                result = self._call_quick_search(payload, db=db)

            set_exact_cache.assert_called_once()
            self.assertFalse(result["meta"]["search_cache"]["exact_hit"])
            self.assertEqual(result["meta"]["search_cache"]["search_fingerprint"][:11], "fsm_search_")
            self.assertEqual(result["meta"]["search_cache"]["freshness"]["status"], "fresh")
        finally:
            db.close()
            engine.dispose()

    def test_fare_memory_flags_can_disable_new_layers_without_breaking_search(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            destination={"seed_iata": "DUB", "include_nearby": False, "radius_km": 250, "max_candidates": 1},
            execution={"max_pairs": 1, "max_requests": 1, "timeout_ms": 3000, "concurrency_limit": 1},
        )

        engine, testing_session_local, db = _db_session()
        try:
            execute_plan_calls = []

            def fake_execute_plan(*args, **kwargs):
                execute_plan_calls.append(kwargs)
                return (
                    [("LEI", "DUB", dt.date(2026, 6, 14), _flight(55, "10:00"))],
                    {
                        "provider_calls": 1,
                        "cache_hits": 0,
                        "cache_misses": 1,
                        "l1_cache_hits": 0,
                        "l2_cache_hits": 0,
                        "negative_cache_hits": 0,
                        "provider_failures": 0,
                        "requested_units_count": 1,
                        "executed_pairs_count": 1,
                        "skipped_pairs_count": 0,
                        "timed_out_units_count": 0,
                        "provider_statuses": [],
                        "warnings_structured_events": [],
                    },
                    [],
                )

            with (
                patch("app.api.v1.search.QUICK_SEARCH_SHARED_CACHE_ENABLED", True),
                patch("app.api.v1.search.FARE_MEMORY_SEARCH_CACHE_ENABLED", False),
                patch("app.api.v1.search.FARE_MEMORY_NEGATIVE_CACHE_ENABLED", False),
                patch("app.api.v1.search.FARE_MEMORY_OFFER_CACHE_ENABLED", False),
                patch("app.api.v1.search.SessionLocal", testing_session_local),
                patch("app.api.v1.search.get_exact_search_cache_entry") as exact_get,
                patch("app.api.v1.search.set_exact_search_cache_entry") as exact_set,
                patch("app.api.v1.search.get_fresh_negative_cache_entry") as negative_get,
                patch("app.api.v1.search.set_negative_cache_entry") as negative_set,
                patch("app.api.v1.search.persist_ranked_result_observations") as persist_observations,
                patch("app.api.v1.search.execute_plan", side_effect=fake_execute_plan),
            ):
                result = self._call_quick_search(payload, db=db)

            exact_get.assert_not_called()
            exact_set.assert_not_called()
            negative_get.assert_not_called()
            negative_set.assert_not_called()
            persist_observations.assert_not_called()
            self.assertEqual(len(execute_plan_calls), 1)
            self.assertIsNone(execute_plan_calls[0]["negative_cache_get"])
            self.assertIsNone(execute_plan_calls[0]["negative_cache_set"])
            self.assertEqual(len(result["results"]), 1)
            self.assertFalse(result["meta"]["search_cache"]["exact_hit"])
        finally:
            db.close()
            engine.dispose()

    def test_partial_provider_results_are_marked_warm_for_revalidation(self):
        payload = self._payload()

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            return ProviderFetchResult(
                flights=[_flight(77, "14:20", source="duffel-offers")],
                warnings=["ryanair_fares_failed_partial"],
            )

        with _patch_request_provider(side_effect=fake_fetch):
            result = self._call_quick_search(payload)

        self.assertEqual(result["results"][0]["freshness"]["status"], "warm")
        self.assertTrue(result["results"][0]["freshness"]["requires_revalidation"])
        self.assertTrue(result["results"][0]["stale_data"])
        self.assertEqual(result["meta"]["search_cache"]["freshness"]["status"], "warm")
        self.assertTrue(result["meta"]["search_cache"]["requires_revalidation"])
        self.assertEqual(result["meta"]["pipeline_counters"]["stale_served_count"], 1)
        self.assertGreaterEqual(result["meta"]["pipeline_counters"]["avg_price_age_seconds"], 0.0)

    def test_provider_status_exposes_aggregated_shape(self):
        payload = self._payload()
        with _patch_request_provider(return_value=[_flight(80, "12:10")]):
            result = self._call_quick_search(payload)

        provider_status = result["meta"]["provider_status"]
        self.assertIn("providers", provider_status)
        self.assertIn("overall_status", provider_status)
        self.assertIsInstance(provider_status["providers"], list)

    def test_provider_status_lists_wizzair_without_breaking_ryanair_legacy_fields(self):
        payload = self._payload()
        with patch.dict(
            "os.environ",
            {
                "FLIGHT_PROVIDER_ORDER": "ryanair,wizzair",
                "FLIGHT_PROVIDER_NON_CORE_ENABLED": "true",
                "FLIGHT_PROVIDER_DUFFEL_ENABLED": "false",
                "FLIGHT_PROVIDER_RYANAIR_ENABLED": "true",
                "FLIGHT_PROVIDER_WIZZAIR_ENABLED": "true",
            },
            clear=False,
        ):
            provider_instance = FlightSearchOrchestrator()

        with (
            patch.object(
                provider_instance,
                "get_flights",
                return_value=[_flight(80, "12:10", source="ryanair-public-fares")],
            ),
            patch("app.api.v1.search._build_request_provider", return_value=provider_instance),
        ):
            result = self._call_quick_search(payload)

        provider_status = result["meta"]["provider_status"]
        self.assertEqual([item["id"] for item in provider_status["providers"]], ["ryanair", "wizzair"])
        self.assertEqual(provider_status["overall_status"], "ok")
        self.assertEqual(provider_status["provider"], "ryanair")
        self.assertEqual(provider_status["legacy"]["provider"], "ryanair")

    def test_ai_preference_marks_single_result_without_reordering(self):
        payload = self._payload(
            origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3},
            execution={"max_pairs": 6, "max_requests": 6, "timeout_ms": 3000, "concurrency_limit": 2},
        )

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
            if origin == "LEI":
                return [_flight(55, "09:00")]
            return [_flight(49, "11:00")]

        def fake_ai_preference(results, *, query_context):
            return QuickSearchAiPreferenceResult(
                enabled=True,
                source="ai",
                preferred_result_id=results[1]["result_id"],
                fallback_used=False,
                reason="Precio recomendado por equilibrio.",
                failure_reason=None,
            )

        with (
            _patch_request_provider(side_effect=fake_fetch),
            patch(
                "app.api.v1.search.select_quick_search_ai_preference",
                side_effect=fake_ai_preference,
            ),
        ):
            result = self._call_quick_search(payload)

        self.assertGreaterEqual(len(result["results"]), 2)
        self.assertEqual(result["results"][0]["origin"], "LEI")
        preferred = [item for item in result["results"] if item["ai_preferred"]]
        self.assertEqual(len(preferred), 1)
        self.assertEqual(preferred[0]["result_id"], result["results"][1]["result_id"])
        self.assertEqual(preferred[0]["ai_preferred_reason"], "Precio recomendado por equilibrio.")
        self.assertEqual(result["meta"]["ai_preference"]["preferred_result_id"], result["results"][1]["result_id"])


if __name__ == "__main__":
    unittest.main()
