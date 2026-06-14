import datetime as dt

import pytest

from app.services.fare_memory import build_freshness_payload


def test_build_freshness_payload_for_fresh_result() -> None:
    observed_at = dt.datetime(2026, 6, 14, 10, 15)
    expires_at = dt.datetime(2026, 6, 14, 12, 15)
    now = dt.datetime(2026, 6, 14, 10, 22)

    payload = build_freshness_payload(
        status="fresh",
        observed_at=observed_at,
        expires_at=expires_at,
        source="provider_cache",
        now=now,
        confidence_score=0.91,
        validation_status="revalidated",
    )

    assert payload == {
        "status": "fresh",
        "observed_at": "2026-06-14T10:15:00Z",
        "expires_at": "2026-06-14T12:15:00Z",
        "age_seconds": 420,
        "confidence_score": 0.91,
        "source": "provider_cache",
        "requires_revalidation": False,
        "validation_status": "revalidated",
    }


def test_build_freshness_payload_marks_warm_result_for_revalidation() -> None:
    payload = build_freshness_payload(
        status="warm",
        observed_at=dt.datetime(2026, 6, 14, 8, 0),
        expires_at=dt.datetime(2026, 6, 14, 10, 0),
        source="provider_cache",
        now=dt.datetime(2026, 6, 14, 8, 38),
    )

    assert payload["requires_revalidation"] is True
    assert payload["confidence_score"] == 0.72
    assert payload["age_seconds"] == 2280


def test_build_freshness_payload_handles_missing_expiration() -> None:
    payload = build_freshness_payload(
        status="provider_error_fresh",
        observed_at=dt.datetime(2026, 6, 14, 8, 0),
        expires_at=None,
        source="provider_backoff",
        now=dt.datetime(2026, 6, 14, 8, 3),
    )

    assert payload["expires_at"] is None
    assert payload["requires_revalidation"] is True


def test_build_freshness_payload_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="Unsupported freshness status"):
        build_freshness_payload(
            status="unknown",
            observed_at=dt.datetime(2026, 6, 14, 8, 0),
            expires_at=None,
            source="provider_cache",
        )
