import datetime as dt
import unittest

from app.domain.entities import ProviderFlight
from app.services.quick_search_dedupe import dedupe_ranked_results
from app.services.quick_search_ranking import RankedResult


def _ranked(
    *,
    origin: str,
    destination: str,
    date_value: dt.date,
    dep: str,
    price: float,
    final_score: float,
    pair_category: str,
    origin_seed_iata: str = "LEI",
    destination_seed_iata: str = "DUB",
    origin_is_seed: bool = True,
    destination_is_seed: bool = True,
    od_km: float = 0.0,
    dd_km: float = 0.0,
):
    return RankedResult(
        origin=origin,
        destination=destination,
        travel_date=date_value,
        flight=ProviderFlight(
            price=price,
            currency="EUR",
            departure_time_local=dep,
            captured_at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
            source="test-provider",
        ),
        final_score=final_score,
        score_breakdown={
            "final_score": final_score,
            "price_component": 0.0,
            "origin_seed_penalty": 0.0,
            "destination_seed_penalty": 0.0,
            "distance_penalty_total": od_km + dd_km,
            "pair_category": pair_category,
        },
        origin_seed_iata=origin_seed_iata,
        destination_seed_iata=destination_seed_iata,
        origin_is_seed=origin_is_seed,
        destination_is_seed=destination_is_seed,
        origin_distance_from_seed_km=od_km,
        destination_distance_from_seed_km=dd_km,
        pair_category=pair_category,
        discovery_explanation="direct_seed" if pair_category == "seed-seed" else "nearby_origin",
    )


class QuickSearchDedupeTests(unittest.TestCase):
    def test_exact_semantic_duplicates_are_collapsed(self):
        rows = [
            _ranked(origin="LEI", destination="DUB", date_value=dt.date(2026, 6, 1), dep="10:00", price=50, final_score=8, pair_category="seed-seed"),
            _ranked(origin="LEI", destination="DUB", date_value=dt.date(2026, 6, 1), dep="10:00", price=50, final_score=8, pair_category="seed-seed"),
        ]
        out = dedupe_ranked_results(rows)
        self.assertEqual(len(out.results), 1)
        self.assertEqual(out.meta["deduped_count"], 1)

    def test_competing_duplicates_keep_best_scored(self):
        rows = [
            _ranked(origin="LEI", destination="DUB", date_value=dt.date(2026, 6, 1), dep="10:00", price=55, final_score=15, pair_category="seed-seed"),
            _ranked(origin="LEI", destination="DUB", date_value=dt.date(2026, 6, 1), dep="10:00", price=58, final_score=9, pair_category="seed-seed"),
        ]
        out = dedupe_ranked_results(rows)
        self.assertEqual(len(out.results), 1)
        self.assertEqual(out.results[0].final_score, 9)

    def test_ranking_order_remains_stable_after_dedupe(self):
        rows = [
            _ranked(origin="LEI", destination="DUB", date_value=dt.date(2026, 6, 1), dep="10:00", price=50, final_score=8, pair_category="seed-seed"),
            _ranked(origin="AGP", destination="DUB", date_value=dt.date(2026, 6, 1), dep="09:00", price=45, final_score=20, pair_category="nearby-seed", origin_is_seed=False, od_km=180),
        ]
        out = dedupe_ranked_results(rows)
        self.assertEqual(out.results[0].origin, "LEI")


if __name__ == "__main__":
    unittest.main()
