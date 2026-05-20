import datetime as dt
import unittest

try:
    from app.api.v1.search import _normalize_quick_search_request
except Exception:  # pragma: no cover
    _normalize_quick_search_request = None


@unittest.skipIf(_normalize_quick_search_request is None, "backend dependencies not available")
class QuickSearchContractAlignmentTests(unittest.TestCase):
    def _base_query(self, **overrides):
        query = {
            "origin_iata": "LEI",
            "destination_iata": "TSF",
            "travel_date": dt.date(2026, 3, 29),
            "radius_km": 150,
            "include_stops": False,
            "include_nearby_origins": False,
            "include_nearby_destinations": False,
            "depart_after": None,
            "depart_before": None,
            "max_stops": 0,
            "exclude_origins": None,
            "exclude_destinations": None,
            "strict_filters": True,
            "soft_filters_weight": 0.6,
            "flex_days_before": 0,
            "flex_days_after": 0,
        }
        query.update(overrides)
        return query

    def test_frontend_style_seed_only_request_is_accepted(self):
        canonical, *_ = _normalize_quick_search_request(payload_dict=None, query_overrides=self._base_query())
        self.assertEqual(canonical.origin.seed_iata, "LEI")
        self.assertEqual(canonical.destination.seed_iata, "TSF")
        self.assertFalse(canonical.origin.include_nearby)
        self.assertFalse(canonical.destination.include_nearby)
        self.assertEqual(canonical.pagination.page, 1)
        self.assertEqual(canonical.pagination.page_size, 10)

    def test_legacy_radius_zero_is_normalized_when_nearby_disabled(self):
        canonical, *_ = _normalize_quick_search_request(
            payload_dict=None,
            query_overrides=self._base_query(radius_km=0, include_nearby_origins=False, include_nearby_destinations=False),
        )
        self.assertEqual(canonical.origin.radius_km, 150)
        self.assertEqual(canonical.destination.radius_km, 150)

    def test_side_independence_for_nearby_toggles(self):
        canonical, *_ = _normalize_quick_search_request(
            payload_dict=None,
            query_overrides=self._base_query(include_nearby_origins=True, include_nearby_destinations=False, radius_km=180),
        )
        self.assertTrue(canonical.origin.include_nearby)
        self.assertFalse(canonical.destination.include_nearby)
        self.assertEqual(canonical.origin.radius_km, 180)
        self.assertEqual(canonical.destination.radius_km, 180)

    def test_canonical_seed_iata_list_is_normalized_and_preserved(self):
        payload = {
            "origin": {
                "seed_iata": "fco",
                "seed_iata_list": ["MXP", "FCO", "mxp", "CIA"],
                "include_nearby": False,
                "radius_km": 150,
                "max_candidates": 6,
            },
            "destination": {
                "seed_iata": "mad",
                "seed_iata_list": ["BCN", "MAD", "GRO"],
                "include_nearby": False,
                "radius_km": 150,
                "max_candidates": 6,
            },
            "travel": {"date": "2026-05-21", "flex_before": 0, "flex_after": 0},
        }
        canonical, origin_list, destination_list, contract = _normalize_quick_search_request(payload_dict=payload, query_overrides={})
        self.assertEqual(canonical.origin.seed_iata, origin_list[0])
        self.assertEqual(canonical.destination.seed_iata, destination_list[0])
        self.assertGreaterEqual(len(origin_list), 2)
        self.assertGreaterEqual(len(destination_list), 2)
        self.assertEqual(canonical.origin.seed_iata_list, origin_list)
        self.assertEqual(canonical.destination.seed_iata_list, destination_list)
        self.assertIn("seed_pool", contract)

    def test_legacy_array_origin_destination_feed_seed_iata_list(self):
        canonical, origin_list, destination_list, _ = _normalize_quick_search_request(
            payload_dict={
                "origin_iata": ["FCO", "MXP", "CIA"],
                "destination_iata": ["MAD", "BCN", "GRO"],
                "travel_date": "2026-05-21",
            },
            query_overrides={},
        )
        self.assertEqual(canonical.origin.seed_iata, origin_list[0])
        self.assertEqual(canonical.destination.seed_iata, destination_list[0])
        self.assertEqual(canonical.origin.seed_iata_list, origin_list)
        self.assertEqual(canonical.destination.seed_iata_list, destination_list)

    def test_seed_pool_contract_exposes_requested_and_effective_scope(self):
        _, origin_list, destination_list, contract = _normalize_quick_search_request(
            payload_dict={
                "origin_iata": ["FCO", "MXP", "FCO"],
                "destination_iata": ["MAD", "BCN", "MAD"],
                "travel_date": "2026-05-21",
            },
            query_overrides={},
        )
        seed_pool = contract["seed_pool"]
        self.assertEqual(seed_pool["origin_requested_count"], 2)
        self.assertEqual(seed_pool["destination_requested_count"], 2)
        self.assertEqual(seed_pool["origin_effective_iata"], origin_list)
        self.assertEqual(seed_pool["destination_effective_iata"], destination_list)


if __name__ == "__main__":
    unittest.main()
