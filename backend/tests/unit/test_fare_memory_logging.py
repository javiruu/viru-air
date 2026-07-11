import json
import logging

from app.services.fare_memory_logging import (
    log_fare_memory_quick_search_counters,
    log_fare_memory_retention_pruned,
    log_fare_memory_watchlist_backfill_applied,
)


def _messages(caplog):
    return [json.loads(record.message) for record in caplog.records]


def test_quick_search_counter_logs_emit_aggregate_cache_events(caplog) -> None:
    counters = {
        "cache_hits": 3,
        "cache_misses": 2,
        "l1_cache_hits": 1,
        "l2_cache_hits": 1,
        "negative_cache_hits": 1,
        "provider_calls_avoided": 3,
    }

    with caplog.at_level(logging.INFO, logger="app.fare_memory.metrics"):
        log_fare_memory_quick_search_counters(query_trace_id="trace_123", pipeline_counters=counters)

    payloads = _messages(caplog)
    events = {payload["event"] for payload in payloads}

    assert events == {
        "fare_memory_cache_hit",
        "fare_memory_cache_miss",
        "fare_memory_provider_call_avoided",
        "fare_memory_negative_cache_hit",
    }
    assert all(payload["query_trace_id"] == "trace_123" for payload in payloads)
    assert "payload_json" not in caplog.text
    assert "canonical_request_json" not in caplog.text
    assert "user_id" not in caplog.text


def test_backfill_log_emits_only_when_snapshots_are_inserted(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.fare_memory.metrics"):
        log_fare_memory_watchlist_backfill_applied(
            candidates_count=4,
            inserted_count=0,
            source="quick_search_save_result",
        )
        log_fare_memory_watchlist_backfill_applied(
            candidates_count=4,
            inserted_count=2,
            source="quick_search_save_result",
        )

    payloads = _messages(caplog)

    assert len(payloads) == 1
    assert payloads[0] == {
        "event": "fare_memory_watchlist_backfill_applied",
        "candidates_count": 4,
        "inserted_count": 2,
        "source": "quick_search_save_result",
    }


def test_retention_log_uses_safe_totals_only(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.fare_memory.metrics"):
        log_fare_memory_retention_pruned(
            {
                "dry_run": False,
                "tables": [{"table": "quick_search_cache_entry"}],
                "totals": {"candidates": 8, "deleted": 5},
                "payload_json": "must-not-be-logged",
            }
        )

    payloads = _messages(caplog)

    assert payloads == [
        {
            "event": "fare_memory_retention_pruned",
            "dry_run": False,
            "candidates": 8,
            "deleted": 5,
            "table_count": 1,
        }
    ]
    assert "must-not-be-logged" not in caplog.text
