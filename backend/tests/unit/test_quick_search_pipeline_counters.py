from app.api.v1.search import _enrich_pipeline_counters


def test_pipeline_counters_measure_initial_provider_miss() -> None:
    response_payload = {
        "meta": {
            "execution": {
                "provider_calls": 1,
                "cache_hits": 0,
                "cache_misses": 1,
                "l1_cache_hits": 0,
                "l2_cache_hits": 0,
                "negative_cache_hits": 0,
                "provider_failures": 0,
            },
            "pipeline_counters": {},
        },
        "results": [
            {
                "stale_data": False,
                "freshness": {"requires_revalidation": False, "status": "fresh", "age_seconds": 30},
            }
        ],
    }

    _enrich_pipeline_counters(response_payload)

    counters = response_payload["meta"]["pipeline_counters"]
    assert counters["provider_calls"] == 1
    assert counters["cache_hits"] == 0
    assert counters["cache_misses"] == 1
    assert counters["provider_calls_avoided"] == 0
    assert counters["cache_hit_rate"] == 0.0
    assert counters["provider_error_rate"] == 0.0
    assert counters["stale_served_count"] == 0
    assert counters["avg_price_age_seconds"] == 30.0


def test_pipeline_counters_measure_cache_hit_api_savings() -> None:
    response_payload = {
        "meta": {
            "execution": {
                "provider_calls": 0,
                "cache_hits": 1,
                "cache_misses": 0,
                "l1_cache_hits": 0,
                "l2_cache_hits": 1,
                "negative_cache_hits": 0,
                "provider_failures": 0,
            },
            "pipeline_counters": {},
        },
        "results": [
            {
                "stale_data": True,
                "freshness": {"requires_revalidation": True, "status": "warm", "age_seconds": 90},
            }
        ],
    }

    _enrich_pipeline_counters(response_payload)

    counters = response_payload["meta"]["pipeline_counters"]
    assert counters["provider_calls"] == 0
    assert counters["l2_cache_hits"] == 1
    assert counters["provider_calls_avoided"] == 1
    assert counters["cache_hit_rate"] == 1.0
    assert counters["stale_served_count"] == 1
    assert counters["avg_price_age_seconds"] == 90.0


def test_pipeline_counters_measure_negative_cache_savings() -> None:
    response_payload = {
        "meta": {
            "execution": {
                "provider_calls": 0,
                "cache_hits": 1,
                "cache_misses": 0,
                "l1_cache_hits": 0,
                "l2_cache_hits": 0,
                "negative_cache_hits": 1,
                "provider_failures": 0,
            },
            "pipeline_counters": {},
        },
        "results": [],
    }

    _enrich_pipeline_counters(response_payload)

    counters = response_payload["meta"]["pipeline_counters"]
    assert counters["negative_cache_hits"] == 1
    assert counters["provider_calls_avoided"] == 1
    assert counters["negative_cache_hit_rate"] == 1.0
    assert counters["provider_calls"] == 0
