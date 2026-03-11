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


if __name__ == "__main__":
    unittest.main()
