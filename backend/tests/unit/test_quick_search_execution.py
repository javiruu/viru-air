import datetime as dt
import unittest

from app.domain.entities import ProviderFlight
from app.services.quick_search_execution import build_execution_plan, execute_plan
from app.services.quick_search_planner import PairPlanItem


class QuickSearchExecutionTests(unittest.TestCase):
    def _pair(self, o: str, d: str, score: float, reason: str) -> PairPlanItem:
        return PairPlanItem(
            origin_iata=o,
            destination_iata=d,
            origin_seed_iata="LEI",
            destination_seed_iata="DUB",
            origin_is_seed=o == "LEI",
            destination_is_seed=d == "DUB",
            origin_distance_from_seed_km=0.0 if o == "LEI" else 100.0,
            destination_distance_from_seed_km=0.0 if d == "DUB" else 100.0,
            pair_priority_score=score,
            pair_reason=reason,
        )

    def test_build_execution_plan_respects_max_requests(self):
        pairs = [
            self._pair("LEI", "DUB", 0.0, "seed-seed"),
            self._pair("LEI", "ORK", 1000.0, "seed-nearby"),
        ]
        dates = [dt.date(2026, 6, 1), dt.date(2026, 6, 2)]
        plan = build_execution_plan(pairs, dates, max_requests=2)
        self.assertEqual(len(plan.units), 2)
        self.assertEqual(plan.waves["wave_1"], 2)

    def test_execute_plan_uses_cache(self):
        pairs = [self._pair("LEI", "DUB", 0.0, "seed-seed")]
        dates = [dt.date(2026, 6, 1)]
        plan = build_execution_plan(pairs, dates, max_requests=5)

        calls = {"n": 0}

        def fake_fetch(origin: str, destination: str, date_str: str, timeout_ms: int):
            calls["n"] += 1
            return [
                ProviderFlight(
                    price=19.99,
                    currency="EUR",
                    departure_time_local="10:00",
                    captured_at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
                    source="test",
                )
            ]

        rows1, meta1, _ = execute_plan(plan, concurrency_limit=2, timeout_ms=3000, fetch_flights=fake_fetch)
        rows2, meta2, _ = execute_plan(plan, concurrency_limit=2, timeout_ms=3000, fetch_flights=fake_fetch)

        self.assertEqual(len(rows1), 1)
        self.assertEqual(len(rows2), 1)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(meta2["cache_hits"], 1)


if __name__ == "__main__":
    unittest.main()
