import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from app.main import app
except Exception:  # pragma: no cover
    TestClient = None
    app = None


@unittest.skipIf(TestClient is None or app is None, "fastapi test dependencies not available")
class QuickSearchObservabilityTests(unittest.TestCase):
    def test_query_trace_and_debug_metadata_present(self):
        client = TestClient(app)
        payload = {
            "origin": {"seed_iata": "LEI", "include_nearby": False},
            "destination": {"seed_iata": "DUB", "include_nearby": False},
            "travel": {"date": "2026-06-14"},
            "execution": {"max_pairs": 4, "max_requests": 4, "timeout_ms": 2000, "concurrency_limit": 2},
        }

        with patch("app.api.v1.search.provider.get_flights", return_value=[]):
            response = client.post("/api/v1/search/quick?debug=true", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("meta", data)
        self.assertIn("query_trace_id", data["meta"])
        self.assertIn("pipeline_metrics", data["meta"])
        self.assertIn("pipeline_counters", data["meta"])
        self.assertIn("warnings_structured", data["meta"])
        self.assertIn("execution", data["meta"])


if __name__ == "__main__":
    unittest.main()
