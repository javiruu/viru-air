from unittest.mock import patch

from app.domain.entities import ProviderFetchResult, ProviderWarning


class _FakeProvider:
    def get_flights(self, origin: str, destination: str, date: str, timeout_ms: int, currency: str = "EUR"):
        return []

    def provider_ids(self) -> list[str]:
        return ["ryanair", "wizzair"]


def test_query_trace_and_debug_metadata_present(client):
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

    assert response.status_code == 200
    data = response.json()

    assert "meta" in data
    assert "query_trace_id" in data["meta"]
    assert "pipeline_metrics" in data["meta"]
    assert "pipeline_counters" in data["meta"]
    assert "warnings_structured" in data["meta"]
    assert "execution" in data["meta"]
    assert "cache_hit_rate" in data["meta"]["pipeline_counters"]
    assert "negative_cache_hit_rate" in data["meta"]["pipeline_counters"]
    assert "provider_calls_avoided" in data["meta"]["pipeline_counters"]
    assert "stale_served_count" in data["meta"]["pipeline_counters"]
    assert "avg_price_age_seconds" in data["meta"]["pipeline_counters"]
    assert "provider_error_rate" in data["meta"]["pipeline_counters"]
    codes = {w.get("code") for w in data["meta"].get("warnings_structured", [])}
    assert "unsupported_filter" in codes
    assert "strict_filter_not_enforceable" in codes


def test_provider_status_errors_feed_pipeline_counters(client):
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

    with patch("app.api.v1.search._build_request_provider", return_value=_EasyJetOutageProvider()):
        response = client.post("/api/v1/search/quick?debug=true", json=payload)

    assert response.status_code == 200
    data = response.json()
    provider_status = data["meta"]["provider_status"]
    counters = data["meta"]["pipeline_counters"]
    assert provider_status["overall_status"] == "total_outage"
    assert provider_status["providers"][0]["id"] == "easyjet"
    assert provider_status["providers"][0]["errors"] == 1
    assert counters["provider_calls"] == 1
    assert counters["provider_failures_count"] == 1
    assert counters["provider_error_rate"] == 1.0
