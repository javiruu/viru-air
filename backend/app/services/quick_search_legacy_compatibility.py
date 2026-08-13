from __future__ import annotations

import os

from app.core.errors import ApiError
from app.services.fare_memory_logging import log_quick_search_legacy_aliases_used


def should_block_quick_search_legacy_aliases(aliases: list[str]) -> bool:
    """Return whether the explicitly configured canary rejects deprecated aliases."""
    mode = os.getenv("QUICK_SEARCH_LEGACY_ALIASES_MODE", "observe").strip().lower()
    return bool(aliases) and mode == "block"


def enforce_quick_search_legacy_alias_policy(aliases: list[str]) -> None:
    """Measure deprecated aliases and reject them only in an explicit canary."""
    log_quick_search_legacy_aliases_used(
        aliases=aliases,
        app_env=os.getenv("APP_ENV", "local"),
    )
    if should_block_quick_search_legacy_aliases(aliases):
        raise ApiError(
            status=400,
            code="quick_search_legacy_aliases_blocked",
            message="Quick-search legacy aliases are disabled in this environment.",
            details=[{"aliases": aliases, "contract_version": "quick_search.v2"}],
        )
