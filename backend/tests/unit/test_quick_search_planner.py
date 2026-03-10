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
        self.assertEqual(plan[0].pair_reason, "seed-seed")
        self.assertEqual(stats["total_pairs"], 4)

    def test_pair_reasons_covered(self):
        origins = [
            ExpandedAirportCandidate("LEI", "LEI", True, 0.0, "seed", "catalog"),
            ExpandedAirportCandidate("LEI", "AGP", False, 180.0, "nearby", "catalog"),
        ]
        destinations = [
            ExpandedAirportCandidate("DUB", "DUB", True, 0.0, "seed", "catalog"),
            ExpandedAirportCandidate("DUB", "ORK", False, 120.0, "nearby", "catalog"),
        ]
        plan, _ = build_pair_plan(origins, destinations, max_pairs=10, max_requests=100, date_count=1)
        reasons = {item.pair_reason for item in plan}
        self.assertSetEqual(reasons, {"seed-seed", "seed-nearby", "nearby-seed", "nearby-nearby"})

    def test_max_pairs_applied_after_sorting(self):
        origins = [
            ExpandedAirportCandidate("LEI", "LEI", True, 0.0, "seed", "catalog"),
            ExpandedAirportCandidate("LEI", "AGP", False, 100.0, "nearby", "catalog"),
            ExpandedAirportCandidate("LEI", "ALC", False, 200.0, "nearby", "catalog"),
        ]
        destinations = [ExpandedAirportCandidate("DUB", "DUB", True, 0.0, "seed", "catalog")]

        plan, stats = build_pair_plan(origins, destinations, max_pairs=2, max_requests=2, date_count=2)
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0].origin_iata, "LEI")
        self.assertEqual(plan[1].origin_iata, "AGP")
        self.assertTrue(stats["truncated"])
        self.assertEqual(stats["max_pairs_by_requests"], 1)


if __name__ == "__main__":
    unittest.main()
