from app.services.quick_search_legacy_compatibility import (
    enforce_quick_search_legacy_alias_policy,
    should_block_quick_search_legacy_aliases,
)


def test_legacy_aliases_remain_observed_by_default(monkeypatch) -> None:
    monkeypatch.delenv("QUICK_SEARCH_LEGACY_ALIASES_MODE", raising=False)

    assert not should_block_quick_search_legacy_aliases(["date"])


def test_legacy_aliases_can_be_blocked_in_a_canary(monkeypatch) -> None:
    monkeypatch.setenv("QUICK_SEARCH_LEGACY_ALIASES_MODE", "block")

    assert should_block_quick_search_legacy_aliases(["date"])
    assert not should_block_quick_search_legacy_aliases([])


def test_canonical_requests_are_not_blocked_in_a_canary(monkeypatch) -> None:
    monkeypatch.setenv("QUICK_SEARCH_LEGACY_ALIASES_MODE", "block")

    enforce_quick_search_legacy_alias_policy([])
