from __future__ import annotations

import datetime as dt

from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult
from app.services.quick_search_warning_codes import (
    PROVIDER_ERROR_CODES,
    PROVIDER_INVALID_PRICE_CODES,
    PROVIDER_SCHEMA_CHANGED_CODES,
    PROVIDER_TOTAL_OUTAGE_CODES,
    has_provider_waf_warning,
)


def resolve_negative_cache_write_policy(result: ProviderFetchResult) -> tuple[str, dt.datetime | None]:
    reason = "no_results"
    retry_after_at = None
    warning_codes = set(result.warnings or [])
    if warning_codes & PROVIDER_SCHEMA_CHANGED_CODES:
        reason = "provider_schema_changed"
        retry_after_at = utc_now_naive() + dt.timedelta(minutes=5)
    elif has_provider_waf_warning(warning_codes):
        reason = "provider_waf_challenge"
        retry_after_at = utc_now_naive() + dt.timedelta(minutes=2)
    elif warning_codes & PROVIDER_INVALID_PRICE_CODES:
        reason = "invalid_price"
    elif warning_codes & PROVIDER_TOTAL_OUTAGE_CODES:
        reason = "provider_total_outage"
    elif "provider_rate_limited" in warning_codes:
        reason = "rate_limited"
        retry_after_at = utc_now_naive() + dt.timedelta(minutes=15)
    elif "provider_timeout_partial" in warning_codes:
        reason = "provider_timeout"
        retry_after_at = utc_now_naive() + dt.timedelta(minutes=5)
    elif "provider_circuit_open_partial" in warning_codes:
        reason = "provider_partial_degraded"
        retry_after_at = utc_now_naive() + dt.timedelta(minutes=10)
    elif "provider_error_partial" in warning_codes:
        reason = "provider_partial_degraded"
        retry_after_at = utc_now_naive() + dt.timedelta(minutes=10)
    elif warning_codes & PROVIDER_ERROR_CODES:
        reason = "provider_partial_degraded"
        retry_after_at = utc_now_naive() + dt.timedelta(minutes=10)
    return reason, retry_after_at
