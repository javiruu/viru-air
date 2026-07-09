import datetime as dt
import unittest

from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.services.quick_search_execution import _CACHE, build_execution_plan, execute_plan
from app.services.quick_search_planner import PairPlanItem


CacheKey = tuple[str, str, str, str]
ProviderCall = tuple[str, str, str]


class ExpandedRouteCacheKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        _CACHE.clear()

    def test_expanded_pairs_use_real_route_cache_keys(self) -> None:
        travel_date = dt.date(2026, 12, 25)
        cached_route_key = ("AGP", "ZAG", str(travel_date), "multi")
        l2_store: dict[CacheKey, ProviderFetchResult] = {
            cached_route_key: ProviderFetchResult(
                flights=[self._flight("AGP", "ZAG")],
                warnings=[],
            ),
        }
        lookups: list[CacheKey] = []
        writes: list[CacheKey] = []
        provider_calls: list[ProviderCall] = []
        plan = build_execution_plan(
            [
                self._seed_pair("LEI", "LJU"),
                self._expanded_pair(),
            ],
            [travel_date],
            max_requests=10,
        )

        def l2_get(
            origin: str,
            destination: str,
            date_value: dt.date | str,
            provider: str,
        ) -> ProviderFetchResult | None:
            key = (origin, destination, str(date_value), provider)
            lookups.append(key)
            return l2_store.get(key)

        def l2_set(
            origin: str,
            destination: str,
            date_value: dt.date | str,
            provider: str,
            result: ProviderFetchResult,
        ) -> None:
            key = (origin, destination, str(date_value), provider)
            writes.append(key)
            l2_store[key] = result

        def fake_fetch(
            origin: str,
            destination: str,
            date_value: str,
            timeout_ms: int,
        ) -> ProviderFetchResult:
            provider_calls.append((origin, destination, date_value))
            return ProviderFetchResult(
                flights=[self._flight(origin, destination)],
                warnings=[],
            )

        rows, meta, _warnings = execute_plan(
            plan,
            concurrency_limit=1,
            timeout_ms=3000,
            fetch_flights=fake_fetch,
            shared_cache_get=l2_get,
            shared_cache_set=l2_set,
        )

        row_routes = {
            (origin, destination, str(row_date))
            for origin, destination, row_date, _flight in rows
        }
        self.assertEqual(
            row_routes,
            {("LEI", "LJU", str(travel_date)), ("AGP", "ZAG", str(travel_date))},
        )
        self.assertIn(cached_route_key, lookups)
        self.assertEqual(provider_calls, [("LEI", "LJU", str(travel_date))])
        self.assertEqual(writes, [("LEI", "LJU", str(travel_date), "multi")])
        self.assertEqual(meta["l2_cache_hits"], 1)
        self.assertEqual(meta["provider_calls"], 1)

    def _seed_pair(self, origin: str, destination: str) -> PairPlanItem:
        return PairPlanItem(
            origin_iata=origin,
            destination_iata=destination,
            origin_seed_iata=origin,
            destination_seed_iata=destination,
            origin_is_seed=True,
            destination_is_seed=True,
            origin_distance_from_seed_km=0.0,
            destination_distance_from_seed_km=0.0,
            pair_priority_score=0.0,
            pair_reason="seed-seed",
        )

    def _expanded_pair(self) -> PairPlanItem:
        return PairPlanItem(
            origin_iata="AGP",
            destination_iata="ZAG",
            origin_seed_iata="LEI",
            destination_seed_iata="LJU",
            origin_is_seed=False,
            destination_is_seed=False,
            origin_distance_from_seed_km=190.0,
            destination_distance_from_seed_km=140.0,
            pair_priority_score=2_330_190.0,
            pair_reason="nearby-nearby",
        )

    def _flight(self, origin: str, destination: str) -> ProviderFlight:
        return ProviderFlight(
            price=29.99,
            currency="EUR",
            departure_time_local="14:30",
            captured_at=dt.datetime(2026, 6, 10, 12, 0),
            source=f"{origin}-{destination}-test",
        )


if __name__ == "__main__":
    unittest.main()
