from __future__ import annotations

from unittest.mock import patch

import pytest

from app.hotels.activation import (
    is_hotel_geocoder_enabled,
    is_hotel_provider_ingestion_enabled,
    is_hotel_sweep_enabled,
    resolve_hotel_activation,
)
from app.hotels.geocoder import geocode_city


def test_invalid_profile_fails_closed_even_with_all_flags_enabled(monkeypatch):
    monkeypatch.setenv("HOTEL_PROFILE", "typo_profile")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_GEOCODER_ENABLED", "true")

    decision = resolve_hotel_activation(operation="sweep")

    assert decision.enabled is False
    assert decision.reason_code == "invalid_profile"
    assert decision.external_calls_allowed is False


def test_missing_flags_fail_closed_outside_local_profile(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for name in (
        "HOTEL_PROFILE",
        "HOTEL_FEATURE_ENABLED",
        "HOTEL_SWEEP_ENABLED",
        "HOTEL_GEOCODER_ENABLED",
        "HOTEL_PROVIDER",
        "HOTEL_PROVIDER_MAKCORPS_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)

    decision = resolve_hotel_activation(operation="sweep")

    assert decision.profile == "prod_off"
    assert decision.feature_enabled is False
    assert decision.sweep_enabled is False
    assert decision.geocoder_enabled is False
    assert decision.external_calls_allowed is False
    assert decision.enabled is False
    assert is_hotel_provider_ingestion_enabled() is False
    assert is_hotel_sweep_enabled() is False
    assert is_hotel_geocoder_enabled() is False


def test_local_mock_requires_explicit_profile_and_feature_but_needs_no_external_permission(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.delenv("HOTEL_PROVIDER", raising=False)
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.delenv("HOTEL_SWEEP_ENABLED", raising=False)

    decision = resolve_hotel_activation(operation="ingestion")

    assert decision.profile == "local_demo"
    assert decision.enabled is True
    assert decision.operation == "ingestion"
    assert decision.reason_code == "explicitly_enabled"
    assert decision.provider == "mock"
    assert decision.provider_external is False
    assert decision.external_calls_allowed is True
    assert is_hotel_provider_ingestion_enabled() is True
    assert is_hotel_sweep_enabled() is False


def test_sweep_switch_is_independent_from_read_and_ingestion(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    monkeypatch.delenv("HOTEL_SWEEP_ENABLED", raising=False)

    assert resolve_hotel_activation(operation="read").feature_enabled is True
    assert is_hotel_provider_ingestion_enabled() is True
    assert is_hotel_sweep_enabled() is False

    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    assert is_hotel_sweep_enabled() is True


def test_profile_provider_combinations_fail_closed(monkeypatch):
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")

    mock_in_staging = resolve_hotel_activation(operation="ingestion")
    assert mock_in_staging.reason_code == "invalid_profile_configuration"
    assert mock_in_staging.enabled is False

    monkeypatch.setenv("HOTEL_PROFILE", "local_fixture")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    commercial_in_fixture = resolve_hotel_activation(operation="ingestion")
    assert commercial_in_fixture.reason_code == "invalid_profile_configuration"
    assert commercial_in_fixture.enabled is False


def test_commercial_provider_requires_provider_specific_opt_in(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.delenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", raising=False)

    blocked = resolve_hotel_activation(operation="ingestion")
    assert blocked.external_calls_allowed is False
    assert blocked.reason == "provider_not_explicitly_enabled"
    assert is_hotel_provider_ingestion_enabled() is False

    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.setenv("MAKCORPS_API_KEY", "test-key")
    allowed = resolve_hotel_activation(operation="ingestion")
    assert allowed.external_calls_allowed is True
    assert is_hotel_provider_ingestion_enabled() is True


@pytest.mark.parametrize(
    ("provider", "credentials"),
    [
        ("booking_demand", {"BOOKING_DEMAND_API_TOKEN": "test-token", "BOOKING_DEMAND_AFFILIATE_ID": "test-affiliate"}),
        ("liteapi", {"LITEAPI_API_KEY": "test-key"}),
    ],
)
def test_candidate_providers_require_credentials_and_a_ready_adapter(monkeypatch, provider, credentials):
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", provider)
    monkeypatch.setenv(f"HOTEL_PROVIDER_{provider.upper()}_ENABLED", "true")
    for name in credentials:
        monkeypatch.delenv(name, raising=False)

    missing = resolve_hotel_activation(operation="ingestion")
    assert missing.reason_code == "provider_credentials_missing"
    assert missing.external_calls_allowed is False

    for name, value in credentials.items():
        monkeypatch.setenv(name, value)
    pending = resolve_hotel_activation(operation="ingestion")
    assert pending.reason_code == "provider_adapter_unavailable"
    assert pending.external_calls_allowed is False


def test_provider_override_is_resolved_against_requested_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    monkeypatch.delenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", raising=False)

    decision = resolve_hotel_activation(operation="sweep", provider="makcorps")

    assert decision.provider == "makcorps"
    assert decision.external_calls_allowed is False
    assert decision.reason == "provider_not_explicitly_enabled"


def test_geocoder_off_prevents_request_even_when_feature_is_enabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_GEOCODER_ENABLED", "false")

    with patch("app.hotels.geocoder.requests.get") as request_get:
        assert geocode_city("Madrid") is None
        request_get.assert_not_called()


def test_provider_ingestion_injected_adapter_is_blocked_when_feature_is_off(monkeypatch):
    from app.hotels.ingestion import HotelIngestionService

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "false")

    class ExternalAdapter:
        provider_id = "makcorps"

        def is_enabled(self):
            return True

        def fetch_hotels(self):
            raise AssertionError("external adapter must not be called")

    with patch("app.hotels.activation.resolve_hotel_activation") as resolver:
        resolver.side_effect = resolve_hotel_activation
        with patch.object(ExternalAdapter, "fetch_hotels") as fetch_hotels:
            try:
                HotelIngestionService(object(), provider=ExternalAdapter())
            except ValueError:
                pass
            fetch_hotels.assert_not_called()
