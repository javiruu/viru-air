import unittest
from unittest.mock import patch

from app.services.quick_search_ai_preference import (
    QuickSearchAiPreferenceResult,
    select_quick_search_ai_preference,
)


def _result(
    result_id: str,
    *,
    price_total: float,
    ranking_score: float,
    duration_total_min: int,
    stale_data: bool = False,
    origin_distance_from_seed_km: float = 0.0,
    destination_distance_from_seed_km: float = 0.0,
):
    return {
        "result_id": result_id,
        "origin": "LEI",
        "destination": "DUB",
        "travel_date": "2026-06-14",
        "departure_time_local": "10:00",
        "price_total": price_total,
        "price": price_total,
        "currency": "EUR",
        "duration_total_min": duration_total_min,
        "ranking_score": ranking_score,
        "stale_data": stale_data,
        "origin_distance_from_seed_km": origin_distance_from_seed_km,
        "destination_distance_from_seed_km": destination_distance_from_seed_km,
        "pair_category": "seed-seed",
    }


class QuickSearchAiPreferenceTests(unittest.TestCase):
    def test_uses_ai_response_when_valid(self):
        results = [
            _result("res-1", price_total=55, ranking_score=0.5, duration_total_min=120),
            _result("res-2", price_total=59, ranking_score=0.4, duration_total_min=100),
        ]
        with patch(
            "app.services.quick_search_ai_preference._call_openai_for_preference",
            return_value=({"preferred_result_id": "res-2", "reason": "Precio muy equilibrado."}, None),
        ):
            preferred = select_quick_search_ai_preference(results, query_context={"origin": "LEI", "destination": "DUB"})

        self.assertEqual(
            preferred,
            QuickSearchAiPreferenceResult(
                enabled=True,
                source="ai",
                preferred_result_id="res-2",
                fallback_used=False,
                reason="Precio muy equilibrado.",
                failure_reason=None,
            ),
        )

    def test_falls_back_to_heuristic_when_ai_fails(self):
        results = [
            _result("res-1", price_total=49, ranking_score=0.3, duration_total_min=95),
            _result("res-2", price_total=49, ranking_score=0.8, duration_total_min=180, stale_data=True),
        ]
        with patch(
            "app.services.quick_search_ai_preference._call_openai_for_preference",
            return_value=(None, "openai_error:Timeout"),
        ):
            preferred = select_quick_search_ai_preference(results, query_context={"origin": "LEI", "destination": "DUB"})

        self.assertTrue(preferred.enabled)
        self.assertEqual(preferred.source, "heuristic")
        self.assertTrue(preferred.fallback_used)
        self.assertEqual(preferred.preferred_result_id, "res-1")
        self.assertEqual(preferred.failure_reason, "openai_error:Timeout")

    def test_disables_preference_when_there_are_no_results(self):
        preferred = select_quick_search_ai_preference([], query_context={"origin": "LEI", "destination": "DUB"})
        self.assertFalse(preferred.enabled)
        self.assertIsNone(preferred.preferred_result_id)
        self.assertEqual(preferred.failure_reason, "no_results")


if __name__ == "__main__":
    unittest.main()
