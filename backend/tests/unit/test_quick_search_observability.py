import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.domain.entities import ProviderFetchResult, ProviderWarning
except Exception:  # pragma: no cover
    TestClient = None
    app = None
    ProviderFetchResult = None
    ProviderWarning = None


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

    @unittest.skipIf(
        ProviderFetchResult is None or ProviderWarning is None,
        "provider entity dependencies not available",
    )
    def test_provider_status_errors_feed_pipeline_counters(self):
        class _EasyJetOutageProvider:
            def get_flights(
                self,
                origin: str,
                destination: str,
                date: str,
                timeout_ms: int,
                currency: str = "EUR",
            ):
                return ProviderFetchResult(
                    flights=[],
                    warnings=["easyjet_provider_unavailable_total", "provider_total_outage"],
                    warnings_structured=[
                        ProviderWarning(
                            code="provider_total_outage",
                            provider="easyjet",
                            severity="error",
                        )
                    ],
                )

            def provider_ids(self) -> list[str]:
                return ["easyjet"]

        payload = {
            "origin": {"seed_iata": "BLQ", "include_nearby": False, "radius_km": 150},
            "destination": {"seed_iata": "BER", "include_nearby": False, "radius_km": 150},
            "travel": {"date": "2026-07-04"},
            "constraints": {"strict_filters": True},
            "execution": {"max_pairs": 1, "max_requests": 1, "timeout_ms": 2000, "concurrency_limit": 1},
        }

        client = TestClient(app)
        with patch("app.api.v1.search._build_request_provider", return_value=_EasyJetOutageProvider()):
            response = client.post("/api/v1/search/quick?debug=true", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        provider_status = data["meta"]["provider_status"]
        counters = data["meta"]["pipeline_counters"]
        self.assertEqual(provider_status["overall_status"], "total_outage")
        self.assertEqual(provider_status["providers"][0]["id"], "easyjet")
        self.assertEqual(provider_status["providers"][0]["errors"], 1)
        self.assertEqual(counters["provider_calls"], 1)
        self.assertEqual(counters["provider_failures_count"], 1)
        self.assertEqual(counters["provider_error_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
