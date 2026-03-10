import unittest

from app.infrastructure.airports_catalog import ExpandedAirportCandidate
from app.services.quick_search_planner import build_pair_plan


class QuickSearchPlannerTests(unittest.TestCase):
    def test_seed_pairs_prioritized(self):
        origins = [
            ExpandedAirportCandidate("LEI", "LEI", True, 0.0, "seed", "catalog"),
            ExpandedAirportCandidate("LEI", "AGP", False, 180.0, "nearby", "catalog"),
        ]
        destinations = [
            ExpandedAirportCandidate("DUB", "DUB", True, 0.0, "seed", "catalog"),
            ExpandedAirportCandidate("DUB", "ORK", False, 200.0, "nearby", "catalog"),
        ]

        plan, stats = build_pair_plan(origins, destinations, max_pairs=4, max_requests=20, date_count=1)
        self.assertGreaterEqual(len(plan), 1)
        self.assertEqual(plan[0].origin_iata, "LEI")
        self.assertEqual(plan[0].destination_iata, "DUB")
        self.assertEqual(stats["total_pairs"], 4)

    def test_request_budget_limits_pairs(self):
        origins = [ExpandedAirportCandidate("LEI", "LEI", True, 0.0, "seed", "catalog")]
        destinations = [
            ExpandedAirportCandidate("DUB", "DUB", True, 0.0, "seed", "catalog"),
            ExpandedAirportCandidate("DUB", "ORK", False, 200.0, "nearby", "catalog"),
            ExpandedAirportCandidate("DUB", "SNN", False, 250.0, "nearby", "catalog"),
        ]

        plan, stats = build_pair_plan(origins, destinations, max_pairs=10, max_requests=2, date_count=2)
        self.assertEqual(len(plan), 1)
        self.assertEqual(stats["max_pairs_by_requests"], 1)


if __name__ == "__main__":
    unittest.main()
