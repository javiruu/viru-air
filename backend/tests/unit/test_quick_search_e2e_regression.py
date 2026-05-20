import datetime as dt
import unittest
from unittest.mock import patch

try:
    from app.api.v1.search import quick_search
    from app.domain.entities import ProviderFlight
    from app.services.quick_search_execution import _CACHE
except Exception:  # pragma: no cover
    quick_search = None
    ProviderFlight = None
    _CACHE = None


def _flight(price: float, dep: str, source: str = "test-provider") -> ProviderFlight:
    return ProviderFlight(
        price=price,
        currency="EUR",
        departure_time_local=dep,
        captured_at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
        source=source,
    )


@unittest.skipIf(quick_search is None or ProviderFlight is None, "fastapi app deps not available")
class QuickSearchE2ERegressionTests(unittest.TestCase):
    def setUp(self):
        if _CACHE is not None:
            _CACHE.clear()

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

    def _call_quick_search(self, payload, debug=True, page=None, page_size=None):
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
        )

    def test_seed_only_base_flow(self):
        payload = self._payload()
        with patch("app.api.v1.search.provider.get_flights", return_value=[_flight(55, "10:00")]):
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
        self.assertEqual(first["risk_label"], "low")
        self.assertIsInstance(first["freshness_ts"], str)
        self.assertEqual(first["ranking_score"], first["score"]["final_score"])
        self.assertFalse(first["stale_data"])
        self.assertEqual(first["itinerary_type"], "direct")
        self.assertEqual(first["legs"], [])

    def test_origin_nearby_expansion_is_real(self):
        payload = self._payload(origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 4})

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int):
            if origin == "LEI":
                return [_flight(62, "09:30")]
            if origin == "AGP":
                return [_flight(58, "09:45")]
            return []

        with patch("app.api.v1.search.provider.get_flights", side_effect=fake_fetch):
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

        with patch("app.api.v1.search.provider.get_flights", return_value=[_flight(70, "11:00")]):
            result = self._call_quick_search(payload)

        categories = {item["pair_reason"] for item in result["meta"]["planned_pairs"]}
        self.assertIn("seed-seed", categories)
        self.assertTrue(any(cat in categories for cat in {"seed-nearby", "nearby-seed", "nearby-nearby"}))

    def test_ranking_keeps_seed_reasonable_priority(self):
        payload = self._payload(origin={"seed_iata": "LEI", "include_nearby": True, "radius_km": 260, "max_candidates": 3})

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int):
            if origin == "LEI":
                return [_flight(60, "10:00")]
            if origin == "AGP":
                return [_flight(58, "10:00")]
            return []

        with patch("app.api.v1.search.provider.get_flights", side_effect=fake_fetch):
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
        with patch("app.api.v1.search.provider.get_flights", return_value=[_flight(90, "12:00")]):
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

        def fake_fetch(origin: str, destination: str, date: str, timeout_ms: int):
            if origin == "AGP":
                raise TimeoutError("provider timeout")
            return [_flight(72, "13:00")]

        with patch("app.api.v1.search.provider.get_flights", side_effect=fake_fetch):
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
        with patch("app.api.v1.search.provider.get_flights", return_value=[_flight(60, "10:00")]):
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
        with patch("app.api.v1.search.provider.get_flights", return_value=[_flight(65, "11:00")]):
            result = self._call_quick_search(payload)
        pagination = result["meta"]["pagination"]
        self.assertEqual(pagination["page"], pagination["total_pages"])
        self.assertGreaterEqual(pagination["total_pages"], 1)


if __name__ == "__main__":
    unittest.main()
