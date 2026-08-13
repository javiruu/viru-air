import pytest

from app.hotels.contracts import (
    HotelProviderAdapter,
    ProviderCapabilities,
    ProviderError,
    ProviderResult,
    ProviderWarning,
)


class LegacyFixtureAdapter(HotelProviderAdapter):
    provider_id = "fixture"

    def is_enabled(self) -> bool:
        return True

    def fetch_hotels(self):
        return []


def test_legacy_adapters_expose_conservative_v2_capabilities() -> None:
    capabilities = LegacyFixtureAdapter().capabilities()

    assert isinstance(capabilities, ProviderCapabilities)
    assert capabilities.provider_id == "fixture"
    assert capabilities.contract_version == "hotel-provider-v1"
    assert capabilities.supports_multiple_rooms is None
    assert capabilities.supports_total_fees is None


def test_provider_result_distinguishes_empty_partial_and_errors() -> None:
    empty = ProviderResult[str](
        provider_id="fixture",
        operation="get_rates",
        request_id="request-1",
        status="empty",
    )
    partial = ProviderResult[str](
        provider_id="fixture",
        operation="get_rates",
        request_id="request-2",
        status="partial",
        items=("valid-rate",),
        warnings=(ProviderWarning(code="provider_conditions_incomplete"),),
    )
    limited = ProviderResult[str](
        provider_id="fixture",
        operation="get_rates",
        request_id="request-3",
        status="rate_limited",
        error=ProviderError(code="rate_limited", category="provider", retryable=True, http_status=429),
    )

    assert empty.is_usable is True
    assert partial.is_usable is True
    assert limited.is_usable is False


@pytest.mark.parametrize(
    "result",
    [
        ProviderResult[str](
            provider_id="fixture",
            operation="get_rates",
            request_id="request-valid",
            status="success",
            items=("rate",),
        ),
    ],
)
def test_provider_result_keeps_valid_successes(result: ProviderResult[str]) -> None:
    assert result.items == ("rate",)


def test_provider_result_rejects_ambiguous_status_shapes() -> None:
    with pytest.raises(ValueError, match="hotel_provider_result_partial_evidence_required"):
        ProviderResult[str](
            provider_id="fixture",
            operation="get_rates",
            request_id="request-4",
            status="partial",
        )
    with pytest.raises(ValueError, match="hotel_provider_result_error_required"):
        ProviderResult[str](
            provider_id="fixture",
            operation="get_rates",
            request_id="request-5",
            status="timeout",
        )
