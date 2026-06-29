import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from app.main import app
except Exception:  # pragma: no cover
    TestClient = None
    app = None


class _FakeProvider:
    def get_flights(self, origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
        return []

    def provider_ids(self) -> list[str]:
        return ["ryanair", "wizzair"]


@unittest.skipIf(TestClient is None or app is None, "fastapi test dependencies not available")
class QuickSearchObservabilityTests(unittest.TestCase):
    def test_query_trace_and_debug_metadata_present(self):
        client = TestClient(app)
        payload = {
            "origin": {"seed_iata": "LEI", "include_nearby": False},
            "destination": {"seed_iata": "DUB", "include_nearby": False},
            "travel": {"date": "2026-06-14"},
            "constraints": {
                "strict_filters": True,
                "include_stops": True,
                "max_stops": 1,
                "duration_max_min": 240,
            },
            "execution": {"max_pairs": 4, "max_requests": 4, "timeout_ms": 2000, "concurrency_limit": 2},
        }

        with patch("app.api.v1.search._build_request_provider", return_value=_FakeProvider()):
            response = client.post("/api/v1/search/quick?debug=true", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("meta", data)
        self.assertIn("query_trace_id", data["meta"])
        self.assertIn("pipeline_metrics", data["meta"])
        self.assertIn("pipeline_counters", data["meta"])
        self.assertIn("warnings_structured", data["meta"])
        self.assertIn("execution", data["meta"])
        self.assertIn("cache_hit_rate", data["meta"]["pipeline_counters"])
        self.assertIn("negative_cache_hit_rate", data["meta"]["pipeline_counters"])
        self.assertIn("provider_calls_avoided", data["meta"]["pipeline_counters"])
        self.assertIn("stale_served_count", data["meta"]["pipeline_counters"])
        self.assertIn("avg_price_age_seconds", data["meta"]["pipeline_counters"])
        self.assertIn("provider_error_rate", data["meta"]["pipeline_counters"])
        codes = {w.get("code") for w in data["meta"].get("warnings_structured", [])}
        self.assertIn("unsupported_filter", codes)
        self.assertIn("strict_filter_not_enforceable", codes)


if __name__ == "__main__":
    unittest.main()
