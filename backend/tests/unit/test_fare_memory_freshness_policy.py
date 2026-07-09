import datetime as dt

import pytest

from app.infrastructure.db.models import QuickSearchCacheEntry
from app.services.quick_search_cache_service import (
    build_effective_freshness,
    resolve_ready_cache_ttl_seconds,
)


REFERENCE_NOW = dt.datetime(2026, 6, 15, 10, 0)


def _ready_entry(
    *,
    travel_date: dt.date,
    captured_at_utc: dt.datetime,
    ttl_seconds: int,
) -> QuickSearchCacheEntry:
    return QuickSearchCacheEntry(
        origin_iata="AGP",
        destination_iata="DUB",
        travel_date=travel_date,
        provider="multi",
        status="ready",
        ttl_seconds=ttl_seconds,
        expires_at_utc=captured_at_utc + dt.timedelta(seconds=ttl_seconds),
        captured_at_utc=captured_at_utc,
        last_accessed_at_utc=captured_at_utc,
        payload_json='{"flights":[]}',
        warnings_json="[]",
        source_hash="qs_policy_contract",
    )


def test_past_departure_is_expired_and_requires_revalidation() -> None:
    entry = _ready_entry(
        travel_date=dt.date(2026, 6, 14),
        captured_at_utc=REFERENCE_NOW,
        ttl_seconds=300,
    )

    freshness = build_effective_freshness(entry, now=REFERENCE_NOW)

    assert freshness["status"] == "expired"
    assert freshness["requires_revalidation"] is True
    assert freshness["validation_status"] == "observed"


def test_departure_inside_24h_uses_short_ready_ttl() -> None:
    ttl = resolve_ready_cache_ttl_seconds(
        travel_date=dt.date(2026, 6, 15),
        provider="multi",
        now=REFERENCE_NOW,
    )

    assert ttl == 5 * 60


def test_far_departure_uses_longer_ready_ttl() -> None:
    ttl = resolve_ready_cache_ttl_seconds(
        travel_date=dt.date(2026, 9, 20),
        provider="multi",
        now=REFERENCE_NOW,
    )

    assert ttl == 12 * 60 * 60


@pytest.mark.parametrize("provider", ["manual", "mock", "fixture"])
def test_manual_mock_and_fixture_providers_are_capped(provider: str) -> None:
    ttl = resolve_ready_cache_ttl_seconds(
        travel_date=dt.date(2026, 9, 20),
        provider=provider,
        now=REFERENCE_NOW,
    )

    assert ttl == 15 * 60


def test_half_age_ready_entry_is_warm_never_fresh() -> None:
    ttl_seconds = 60 * 60
    entry = _ready_entry(
        travel_date=dt.date(2026, 6, 20),
        captured_at_utc=REFERENCE_NOW - dt.timedelta(seconds=ttl_seconds // 2),
        ttl_seconds=ttl_seconds,
    )

    freshness = build_effective_freshness(entry, now=REFERENCE_NOW)

    assert freshness["status"] == "warm"
    assert freshness["requires_revalidation"] is True
    assert freshness["validation_status"] == "observed"
