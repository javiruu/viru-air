from __future__ import annotations

from typing import Final

WARNING_CODE_ALIASES: Final[dict[str, str]] = {
    "provider_timeout_parcial": "provider_timeout_partial",
    "ryanair_unavailable_parcial": "ryanair_unavailable_partial",
    "provider_total_outage": "provider_total_outage",
}

PROVIDER_TOTAL_OUTAGE_CODES: Final[frozenset[str]] = frozenset(
    {
        "provider_total_outage",
        "ryanair_provider_unavailable_total",
        "vueling_provider_unavailable_total",
        "wizzair_provider_unavailable_total",
        "easyjet_provider_unavailable_total",
        "iberia_provider_unavailable_total",
        "duffel_provider_unavailable_total",
    }
)

PROVIDER_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "ryanair_availability_failed",
        "ryanair_fares_failed",
    }
)

PROVIDER_PARTIAL_DEGRADATION_CODES: Final[frozenset[str]] = frozenset(
    {
        "provider_error_partial",
        "provider_timeout_partial",
        "provider_partial_results_served",
        "ryanair_unavailable_partial",
        "ryanair_availability_failed_partial",
        "ryanair_fares_failed_partial",
    }
)

UI_WARNING_CRITICAL_CODES: Final[frozenset[str]] = PROVIDER_TOTAL_OUTAGE_CODES | PROVIDER_ERROR_CODES
UI_WARNING_PARTIAL_CODES: Final[frozenset[str]] = PROVIDER_PARTIAL_DEGRADATION_CODES
PROVIDER_WARNING_CODES: Final[frozenset[str]] = (
    PROVIDER_PARTIAL_DEGRADATION_CODES | PROVIDER_TOTAL_OUTAGE_CODES | PROVIDER_ERROR_CODES
)
PROVIDER_OUTAGE_WARNING_CODES: Final[frozenset[str]] = frozenset(
    {
        "provider_error_partial",
        "provider_timeout_partial",
    }
) | PROVIDER_TOTAL_OUTAGE_CODES | PROVIDER_ERROR_CODES


def normalize_warning_code(code: str) -> str:
    return WARNING_CODE_ALIASES.get(code, code)
