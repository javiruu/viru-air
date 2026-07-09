from __future__ import annotations

from typing import Final

from app.domain.entities import ProviderFetchResult


NEGATIVE_REASON_TTL_SECONDS: Final[dict[str, int]] = {
    "no_results": 60 * 60,
    "no_availability": 60 * 60,
    "invalid_price": 15 * 60,
    "provider_timeout": 5 * 60,
    "provider_total_outage": 3 * 60,
    "provider_partial_degraded": 10 * 60,
    "unsupported_route": 12 * 60 * 60,
    "rate_limited": 5 * 60,
}

PROVIDER_BACKOFF_REASONS: Final[frozenset[str]] = frozenset(
    {
        "provider_timeout",
        "provider_error",
        "provider_total_outage",
        "provider_partial_degraded",
        "rate_limited",
    }
)

PROVIDER_ERROR_FRESHNESS_REASONS: Final[frozenset[str]] = PROVIDER_BACKOFF_REASONS

NEGATIVE_REASON_WARNINGS: Final[dict[str, list[str]]] = {
    "provider_timeout": ["provider_timeout_partial"],
    "provider_error": ["provider_error_partial"],
    "provider_total_outage": ["provider_total_outage"],
    "provider_partial_degraded": ["provider_error_partial"],
    "rate_limited": ["provider_rate_limited", "provider_timeout_partial"],
}


def negative_ttl_for_reason(
    reason: str,
    *,
    default_negative_ttl: int,
    default_provider_error_ttl: int,
) -> int:
    if reason in NEGATIVE_REASON_TTL_SECONDS:
        return NEGATIVE_REASON_TTL_SECONDS[reason]
    if reason in PROVIDER_BACKOFF_REASONS:
        return default_provider_error_ttl
    return default_negative_ttl


def is_provider_backoff_reason(reason: str) -> bool:
    return reason in PROVIDER_BACKOFF_REASONS


def negative_freshness_status_for_reason(reason: str) -> str:
    return "provider_error_fresh" if reason in PROVIDER_ERROR_FRESHNESS_REASONS else "negative_fresh"


def negative_result_for_reason(reason: str) -> ProviderFetchResult:
    return ProviderFetchResult(flights=[], warnings=NEGATIVE_REASON_WARNINGS.get(reason, []))
