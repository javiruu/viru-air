import unittest

from app.api.v1.search import _compute_dynamic_execution_budget


class QuickSearchDynamicBudgetTests(unittest.TestCase):
    def test_dynamic_budget_scales_with_multi_seed_flex_and_nearby(self):
        max_pairs, max_requests, signals = _compute_dynamic_execution_budget(
            requested_max_pairs=48,
            requested_max_requests=480,
            origin_pool_count=6,
            destination_pool_count=5,
            flex_before=3,
            flex_after=3,
            include_nearby_origins=True,
            include_nearby_destinations=True,
        )
        self.assertGreaterEqual(max_pairs, 120)
        self.assertGreaterEqual(max_requests, 1600)
        self.assertEqual(signals["pair_complexity"], 30)
        self.assertEqual(signals["date_count"], 7)
        self.assertEqual(signals["nearby_sides"], 2)

    def test_dynamic_budget_keeps_requested_floor_for_small_searches(self):
        max_pairs, max_requests, signals = _compute_dynamic_execution_budget(
            requested_max_pairs=48,
            requested_max_requests=480,
            origin_pool_count=1,
            destination_pool_count=1,
            flex_before=0,
            flex_after=0,
            include_nearby_origins=False,
            include_nearby_destinations=False,
        )
        self.assertEqual(max_pairs, 48)
        self.assertEqual(max_requests, 480)
        self.assertEqual(signals["nearby_sides"], 0)


if __name__ == "__main__":
    unittest.main()
