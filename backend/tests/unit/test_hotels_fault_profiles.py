from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.hotels.fault_profiles import (
    HotelFaultProfileError,
    load_hotel_fault_profiles,
    resolve_hotel_fault_profile,
)
from app.hotels.mock_provider import MockHotelProviderAdapter


@pytest.mark.parametrize(
    ("profile", "expected_status", "error_code"),
    [
        ("happy_path", "success", None),
        ("empty_provider", "empty", None),
        ("rate_limited_429", "rate_limited", "rate_limited"),
        ("provider_timeout", "timeout", "timeout"),
        ("invalid_json", "invalid_response", "invalid_response"),
        ("schema_drift", "invalid_response", "schema_drift"),
        ("rate_without_currency", "invalid_response", "rate_without_currency"),
        ("sold_out", "success", None),
        ("hotel_ambiguous", "partial", "hotel_ambiguous"),
        ("deeplink_invalid", "success", None),
        ("stale_history", "success", None),
        ("partial_batch", "partial", "partial_batch"),
        ("ownership_cross_user", "success", None),
    ],
)
def test_h44_fault_profile_manifest_declares_expected_outcome(profile, expected_status, error_code):
    loaded = load_hotel_fault_profiles()
    selected = resolve_hotel_fault_profile(profile)
    assert selected == loaded[profile]
    assert selected.expected_status == expected_status
    assert selected.error_code == error_code


def test_fault_profile_loader_rejects_unknown_profile(tmp_path: Path):
    manifest = {"version": 1, "profiles": {"not_a_profile": {"mode": "empty", "expected_status": "empty"}}}
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        load_hotel_fault_profiles(path)


def test_mock_empty_profile_makes_no_fixture_mutation(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({"hotels": [{"provider_hotel_id": "x"}]}), encoding="utf-8")
    before = fixture.read_bytes()
    adapter = MockHotelProviderAdapter(str(fixture), fault_profile="empty_provider")
    assert adapter.fetch_hotels() == []
    assert fixture.read_bytes() == before


@pytest.mark.parametrize("profile", ["rate_limited_429", "provider_timeout", "invalid_json", "schema_drift", "rate_without_currency"])
def test_mock_typed_failure_profiles_never_call_network(profile):
    adapter = MockHotelProviderAdapter(fault_profile=profile)
    with pytest.raises(HotelFaultProfileError) as raised:
        adapter.fetch_hotels()
    assert raised.value.profile.name == profile
    assert raised.value.error_code


def test_mock_sold_out_and_invalid_deeplink_profiles_are_explicit():
    sold_out = MockHotelProviderAdapter(fault_profile="sold_out").fetch_hotels()
    assert sold_out[0].rates[0].availability_status == "unavailable"

    invalid_link = MockHotelProviderAdapter(fault_profile="deeplink_invalid").fetch_hotels()
    assert invalid_link[0].rates[0].deep_link == "javascript:alert(1)"


def test_mock_partial_profile_is_deterministic():
    first = MockHotelProviderAdapter(fault_profile="partial_batch").fetch_hotels()
    second = MockHotelProviderAdapter(fault_profile="partial_batch").fetch_hotels()
    assert [item.provider_hotel_id for item in first] == [item.provider_hotel_id for item in second]
    assert len(first) == 1


def test_mock_fetch_hotel_rates_filters_the_targeted_stay():
    adapter = MockHotelProviderAdapter()

    rates = adapter.fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
        guests=2,
        currency="eur",
    )

    assert len(rates) == 1
    assert rates[0].amount == 189.5
    assert rates[0].currency == "EUR"
    assert adapter.fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 8, 1),
        check_out=date(2026, 8, 3),
    ) == []


@pytest.mark.parametrize(
    "profile",
    ["rate_limited_429", "provider_timeout", "invalid_json", "schema_drift", "rate_without_currency"],
)
def test_mock_fetch_hotel_rates_reuses_typed_failure_profiles(profile):
    adapter = MockHotelProviderAdapter(fault_profile=profile)

    with pytest.raises(HotelFaultProfileError) as raised:
        adapter.fetch_hotel_rates(
            hotel_id="mock-sol-001",
            check_in=date(2026, 7, 10),
            check_out=date(2026, 7, 12),
        )

    assert raised.value.profile.name == profile


def test_mock_fetch_hotel_rates_applies_sold_out_and_invalid_deeplink_profiles():
    sold_out = MockHotelProviderAdapter(fault_profile="sold_out").fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
    )
    invalid_link = MockHotelProviderAdapter(fault_profile="deeplink_invalid").fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
    )

    assert sold_out[0].availability_status == "unavailable"
    assert invalid_link[0].deep_link == "javascript:alert(1)"


def test_empty_profile_is_a_targeted_empty_response():
    adapter = MockHotelProviderAdapter(fault_profile="empty_provider")

    assert adapter.fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
    ) == []


def test_advanced_profiles_are_deterministic_for_targeted_rates():
    stale = MockHotelProviderAdapter(fault_profile="stale_history").fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
    )
    ambiguous = MockHotelProviderAdapter(fault_profile="hotel_ambiguous").fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
    )
    partial = MockHotelProviderAdapter(fault_profile="partial_batch").fetch_hotel_rates(
        hotel_id="mock-sol-001",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
    )

    assert [rate.availability_status for rate in stale] == ["stale"]
    assert len(ambiguous) == 1
    assert len(partial) == 1
