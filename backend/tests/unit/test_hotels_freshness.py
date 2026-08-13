from __future__ import annotations

from datetime import datetime, timedelta

from app.services.hotels_service import HotelObservationFreshnessInput, classify_hotel_observation_freshness


def test_observation_freshness_uses_declared_boundaries_and_provenance() -> None:
    now = datetime(2026, 8, 12, 12, 0, 0)

    fresh = classify_hotel_observation_freshness(HotelObservationFreshnessInput(
        observed_at=now - timedelta(minutes=30),
        collected_at=None,
        provider="makcorps",
        now=now,
    ))
    recent = classify_hotel_observation_freshness(HotelObservationFreshnessInput(
        observed_at=now - timedelta(hours=6),
        collected_at=None,
        provider="makcorps",
        now=now,
    ))
    stale = classify_hotel_observation_freshness(HotelObservationFreshnessInput(
        observed_at=now - timedelta(hours=6, seconds=1),
        collected_at=None,
        provider="makcorps",
        now=now,
    ))
    expired = classify_hotel_observation_freshness(HotelObservationFreshnessInput(
        observed_at=now - timedelta(hours=24, seconds=1),
        collected_at=None,
        provider="makcorps",
        now=now,
    ))

    assert fresh.state == "fresh"
    assert recent.state == "recent"
    assert stale.state == "stale"
    assert stale.requires_revalidation is True
    assert expired.state == "expired"
    assert expired.requires_revalidation is True
    assert fresh.provenance_kind == "provider_observed"


def test_observation_freshness_marks_legacy_and_mock_data_without_current_claims() -> None:
    now = datetime(2026, 8, 12, 12, 0, 0)
    legacy = classify_hotel_observation_freshness(HotelObservationFreshnessInput(
        observed_at=None,
        collected_at=now - timedelta(minutes=10),
        provider="makcorps",
        now=now,
    ))
    fixture = classify_hotel_observation_freshness(HotelObservationFreshnessInput(
        observed_at=now - timedelta(minutes=1),
        collected_at=None,
        provider="mock",
        now=now,
    ))
    future = classify_hotel_observation_freshness(HotelObservationFreshnessInput(
        observed_at=now + timedelta(minutes=1),
        collected_at=None,
        provider="makcorps",
        now=now,
    ))

    assert legacy.state == "fresh"
    assert legacy.provenance_kind == "historical_snapshot"
    assert fixture.state == "historical"
    assert fixture.provenance_kind == "fixture_demo"
    assert future.state == "unknown"
