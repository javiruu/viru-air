from __future__ import annotations

import os


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value.strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


FARE_MEMORY_ENABLED = _env_bool("FARE_MEMORY_ENABLED", True)
FARE_MEMORY_SEARCH_CACHE_ENABLED = FARE_MEMORY_ENABLED and _env_bool("FARE_MEMORY_SEARCH_CACHE_ENABLED", True)
FARE_MEMORY_OFFER_CACHE_ENABLED = FARE_MEMORY_ENABLED and _env_bool("FARE_MEMORY_OFFER_CACHE_ENABLED", True)
FARE_MEMORY_NEGATIVE_CACHE_ENABLED = FARE_MEMORY_ENABLED and _env_bool("FARE_MEMORY_NEGATIVE_CACHE_ENABLED", True)
FARE_MEMORY_BOOT_WARMUP_ENABLED = FARE_MEMORY_ENABLED and _env_bool("FARE_MEMORY_BOOT_WARMUP_ENABLED", False)
FARE_MEMORY_MAX_BOOT_JOBS = _env_int("FARE_MEMORY_MAX_BOOT_JOBS", 25, minimum=0)
FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS = _env_int("FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS", 30, minimum=0)
FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE = _env_int(
    "FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE",
    60,
    minimum=1,
)
