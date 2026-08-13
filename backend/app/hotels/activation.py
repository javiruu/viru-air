from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE_VALUES = {"1", "true", "yes", "on"}
_SUPPORTED_PROVIDERS = {"mock", "local_scrape", "makcorps", "booking_demand", "liteapi", "osm_overpass"}
_LOCAL_PROVIDERS = {"mock", "local_scrape"}
_PROVIDER_REQUIRED_ENV = {
    "booking_demand": ("BOOKING_DEMAND_API_TOKEN", "BOOKING_DEMAND_AFFILIATE_ID"),
    "liteapi": ("LITEAPI_API_KEY",),
}
_PROVIDER_ADAPTERS_READY = {"mock", "local_scrape", "makcorps", "osm_overpass"}
_CANONICAL_PROFILES = {
    "local_demo",
    "local_fixture",
    "staging_canary",
    "prod_off",
    "prod_gradual",
}


@dataclass(frozen=True)
class HotelActivation:
    """Effective hotel runtime decisions resolved from the current environment."""

    profile: str
    feature_enabled: bool
    sweep_enabled: bool
    geocoder_enabled: bool
    provider: str
    provider_external: bool
    external_calls_allowed: bool
    reason: str
    operation: str = "read"

    @property
    def enabled(self) -> bool:
        if self.operation == "sweep":
            return self.feature_enabled and self.sweep_enabled and self.external_calls_allowed
        if self.operation == "geocoder":
            return self.feature_enabled and self.geocoder_enabled and self.external_calls_allowed
        if self.operation in {"ingestion", "area_search"}:
            return self.feature_enabled and self.external_calls_allowed
        return self.feature_enabled

    @property
    def reason_code(self) -> str:
        return self.reason


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


def is_hotel_provider_external(provider: str) -> bool:
    return provider.strip().lower() not in _LOCAL_PROVIDERS


def resolve_hotel_activation(
    *,
    operation: str = "read",
    provider: str | None = None,
) -> HotelActivation:
    """Resolve one fail-closed decision shared by API, jobs, and workers.

    Reads remain available when the feature is off. Provider-backed ingestion,
    sweeps, and external geocoding require explicit opt-in. Commercial
    providers additionally require an explicit provider-specific enable flag.
    """
    configured_profile = os.getenv("HOTEL_PROFILE", "").strip().lower()
    profile = configured_profile or "prod_off"
    effective_provider = provider if provider is not None else os.getenv("HOTEL_PROVIDER", "mock")
    provider = effective_provider.strip().lower() or "mock"
    feature_enabled = _env_flag("HOTEL_FEATURE_ENABLED")
    sweep_enabled = _env_flag("HOTEL_SWEEP_ENABLED")
    geocoder_enabled = _env_flag("HOTEL_GEOCODER_ENABLED")
    provider_external = is_hotel_provider_external(provider)

    if provider not in _SUPPORTED_PROVIDERS:
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=False,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=provider_external,
            external_calls_allowed=False,
            reason="invalid_provider",
        )

    if profile not in _CANONICAL_PROFILES:
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=False,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=provider_external,
            external_calls_allowed=False,
            reason="invalid_profile",
        )

    profile_allows_local = profile in {"local_demo", "local_fixture"}
    profile_allows_external = profile in {"staging_canary", "prod_gradual"}
    if (provider in _LOCAL_PROVIDERS and not profile_allows_local) or (provider_external and not profile_allows_external):
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=False,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=provider_external,
            external_calls_allowed=False,
            reason="invalid_profile_configuration",
        )

    if profile == "prod_off":
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=False,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=provider_external,
            external_calls_allowed=False,
            reason="profile_prod_off",
        )

    if not feature_enabled:
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=False,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=provider_external,
            external_calls_allowed=False,
            reason="hotel_feature_disabled",
        )

    provider_enabled = _env_flag(f"HOTEL_PROVIDER_{provider.upper()}_ENABLED")
    if provider_external and not provider_enabled:
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=True,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=True,
            external_calls_allowed=False,
            reason="provider_not_explicitly_enabled",
        )

    missing_credential = next(
        (name for name in _PROVIDER_REQUIRED_ENV.get(provider, ()) if not os.getenv(name, "").strip()),
        None,
    )
    if provider_external and missing_credential is not None:
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=True,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=True,
            external_calls_allowed=False,
            reason="provider_credentials_missing",
        )

    if provider_external and provider not in _PROVIDER_ADAPTERS_READY:
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=True,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=True,
            external_calls_allowed=False,
            reason="provider_adapter_unavailable",
        )

    if operation == "sweep" and provider == "osm_overpass":
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=True,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=True,
            external_calls_allowed=False,
            reason="provider_operation_unsupported",
        )

    if operation == "sweep" and not sweep_enabled:
        return HotelActivation(
            operation=operation,
            profile=profile,
            feature_enabled=True,
            sweep_enabled=False,
            geocoder_enabled=False,
            provider=provider,
            provider_external=provider_external,
            external_calls_allowed=False,
            reason="hotel_sweep_disabled",
        )

    return HotelActivation(
        operation=operation,
        profile=profile,
        feature_enabled=True,
        sweep_enabled=sweep_enabled,
        geocoder_enabled=geocoder_enabled,
        provider=provider,
        provider_external=provider_external,
        external_calls_allowed=not provider_external or provider_enabled,
        reason="explicitly_enabled",
    )


def is_hotel_provider_ingestion_enabled() -> bool:
    decision = resolve_hotel_activation(operation="ingestion")
    return decision.feature_enabled and decision.external_calls_allowed


def is_hotel_sweep_enabled(*, provider: str | None = None) -> bool:
    decision = resolve_hotel_activation(operation="sweep", provider=provider)
    return decision.feature_enabled and decision.sweep_enabled


def is_hotel_geocoder_enabled() -> bool:
    decision = resolve_hotel_activation(operation="geocoder")
    return decision.external_calls_allowed and decision.geocoder_enabled


def is_hotel_canonical_dual_write_enabled() -> bool:
    return _env_flag("HOTEL_CANONICAL_MODEL_ENABLED") and _env_flag(
        "HOTEL_CANONICAL_DUAL_WRITE_ENABLED"
    )
