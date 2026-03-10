import datetime as dt
import unittest

from app.domain.entities import ProviderFlight
from app.services.quick_search_planner import PairPlanItem
from app.services.quick_search_ranking import rank_quick_search_results


class QuickSearchRankingTests(unittest.TestCase):
    def _pair(self, origin: str, destination: str, *, reason: str, origin_seed: bool, destination_seed: bool, od_km: float, dd_km: float):
        return PairPlanItem(
            origin_iata=origin,
            destination_iata=destination,
            origin_seed_iata="LEI",
            destination_seed_iata="DUB",
            origin_is_seed=origin_seed,
            destination_is_seed=destination_seed,
            origin_distance_from_seed_km=od_km,
            destination_distance_from_seed_km=dd_km,
            pair_priority_score=0.0,
            pair_reason=reason,
        )

    def _flight(self, price: float, dep: str = "10:00"):
        return ProviderFlight(
            price=price,
            currency="EUR",
            departure_time_local=dep,
            captured_at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
            source="test",
        )

    def test_seed_seed_preferred_when_price_gap_is_small(self):
        pairs = [
            self._pair("LEI", "DUB", reason="seed-seed", origin_seed=True, destination_seed=True, od_km=0, dd_km=0),
            self._pair("AGP", "ORK", reason="nearby-nearby", origin_seed=False, destination_seed=False, od_km=180, dd_km=120),
        ]
        rows = [
            ("LEI", "DUB", dt.date(2026, 6, 1), self._flight(60)),
            ("AGP", "ORK", dt.date(2026, 6, 1), self._flight(55)),
        ]

        ranked = rank_quick_search_results(rows, pairs)
        self.assertEqual(ranked[0].origin, "LEI")
        self.assertEqual(ranked[0].destination, "DUB")

    def test_nearby_can_win_if_price_gap_is_large(self):
        pairs = [
            self._pair("LEI", "DUB", reason="seed-seed", origin_seed=True, destination_seed=True, od_km=0, dd_km=0),
            self._pair("AGP", "DUB", reason="nearby-seed", origin_seed=False, destination_seed=True, od_km=180, dd_km=0),
        ]
        rows = [
            ("LEI", "DUB", dt.date(2026, 6, 1), self._flight(180)),
            ("AGP", "DUB", dt.date(2026, 6, 1), self._flight(70)),
        ]

        ranked = rank_quick_search_results(rows, pairs)
        self.assertEqual(ranked[0].origin, "AGP")

    def test_distance_penalty_grows_with_deviation(self):
        pairs = [
            self._pair("AGP", "DUB", reason="nearby-seed", origin_seed=False, destination_seed=True, od_km=100, dd_km=0),
            self._pair("ALC", "DUB", reason="nearby-seed", origin_seed=False, destination_seed=True, od_km=250, dd_km=0),
        ]
        rows = [
            ("AGP", "DUB", dt.date(2026, 6, 1), self._flight(80)),
            ("ALC", "DUB", dt.date(2026, 6, 1), self._flight(80)),
        ]

        ranked = rank_quick_search_results(rows, pairs)
        self.assertEqual(ranked[0].origin, "AGP")

    def test_soft_filters_weight_changes_penalty_intensity(self):
        pairs = [
            self._pair("LEI", "DUB", reason="seed-seed", origin_seed=True, destination_seed=True, od_km=0, dd_km=0),
            self._pair("AGP", "DUB", reason="nearby-seed", origin_seed=False, destination_seed=True, od_km=180, dd_km=0),
        ]
        rows = [
            ("LEI", "DUB", dt.date(2026, 6, 1), self._flight(100, dep="11:00")),
            ("AGP", "DUB", dt.date(2026, 6, 1), self._flight(95, dep="10:00")),
        ]

        ranked_soft = rank_quick_search_results(rows, pairs, soft_filters_weight=0.2)
        ranked_strict = rank_quick_search_results(rows, pairs, soft_filters_weight=1.2)
        self.assertLess(
            ranked_soft[1].score_breakdown["distance_penalty_total"],
            ranked_strict[1].score_breakdown["distance_penalty_total"],
        )

    def test_ranking_is_deterministic_with_tie_breakers(self):
        pairs = [
            self._pair("LEI", "DUB", reason="seed-seed", origin_seed=True, destination_seed=True, od_km=0, dd_km=0),
            self._pair("LEI", "ORK", reason="seed-nearby", origin_seed=True, destination_seed=False, od_km=0, dd_km=120),
        ]
        rows = [
            ("LEI", "DUB", dt.date(2026, 6, 1), self._flight(100, dep="11:00")),
            ("LEI", "DUB", dt.date(2026, 6, 1), self._flight(100, dep="10:00")),
            ("LEI", "ORK", dt.date(2026, 6, 1), self._flight(100, dep="09:00")),
        ]

        ranked = rank_quick_search_results(rows, pairs)
        self.assertEqual(ranked[0].flight.departure_time_local, "10:00")
        self.assertIn("final_score", ranked[0].score_breakdown)


if __name__ == "__main__":
    unittest.main()
