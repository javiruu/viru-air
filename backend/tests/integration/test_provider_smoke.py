"""Integration smoke gate for the Iberia + easyJet providers.

This test suite runs in CI as a regression guard: when captcha codes
(`*_provider_captcha_*`) or canonical outage codes (`*_provider_unavailable_*`,
`provider_total_outage`) appear in `warnings_structured`, the test fails with
a precise error so we never silently regress to "blocked-but-looks-ok".

Disabled by default because it performs real network calls. Enable in CI via:

    RUN_PROVIDER_SMOKE=1 uv run pytest backend/tests/integration/test_provider_smoke.py -v

The smoke is intentionally tight (one route per provider, short timeout) so
that even when Akamai keeps denying the request, we still get fast, actionable
failures.
"""

from __future__ import annotations

import os

import pytest

# NB: no module-level ``pytestmark = [...]`` here. The two opt-in network
# smokes below carry their own ``@pytest.mark.integration`` /
# ``@pytest.mark.network`` decorators so they can be filtered by marker. The
# pure unit classifier test does NOT carry those markers — applying them at
# module level would falsely classify a no-network test as a network test
# under ``pytest -m network``.


_BLOCKING_CAPTCHA_FRAGMENTS = (
    "_provider_captcha_",
    "_flight_connections_captcha_",
)
_BLOCKING_OUTAGE_CODES = {
    "provider_total_outage",
    "iberia_provider_unavailable_total",
    "easyjet_provider_unavailable_total",
}


def _smoke_env_enabled() -> bool:
    return os.getenv("RUN_PROVIDER_SMOKE") in {"1", "true", "yes", "on"}


def _summarize(*, name: str, result_warnings: list[str] | None, exception_keywords: list[str] | None) -> str:
    """Build a one-line failure summary so CI logs are actionable."""
    if exception_keywords:
        return f"[{name}] captcha-detected ProviderSourceFetchError: codes={exception_keywords}"
    if result_warnings:
        return f"[{name}] block codes in warnings: {result_warnings}"
    return f"[{name}] clean"


def _extract_codes(warnings_structured) -> list[str]:
    return [w.code for w in warnings_structured]


def _block_codes_in(codes: list[str]) -> list[str]:
    rejected: list[str] = []
    for code in codes:
        if any(fragment in code for fragment in _BLOCKING_CAPTCHA_FRAGMENTS):
            rejected.append(code)
        elif code in _BLOCKING_OUTAGE_CODES:
            rejected.append(code)
    return rejected


@pytest.fixture(scope="module")
def smoke_enabled() -> bool:
    return _smoke_env_enabled()


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.skipif(
    os.getenv("RUN_PROVIDER_SMOKE") not in {"1", "true", "yes", "on"},
    reason=(
        "Skipped by default (real network call). Set RUN_PROVIDER_SMOKE=1 in "
        "CI to enable the live Akamai/Datadome regression guard."
    ),
)
def test_iberia_provider_does_not_get_blocked_by_akamai(smoke_enabled) -> None:
    """Real-network smoke: MAD → JFK on a near-future date.

    Pass = at least one flight OR zero flights with `provider_empty_result`.
    Fail = captcha codes, account-wide outage, or any other error.
    """
    assert smoke_enabled, "smoke disabled; gate should have skipped"

    from app.infrastructure.providers.iberia_provider import IberiaProvider

    provider = IberiaProvider()
    try:
        result = provider.get_flights("MAD", "JFK", "2026-08-15", timeout_ms=10000)
    except Exception as exc:
        codes = list(getattr(exc, "warning_codes", []) or [])
        assert not codes, _summarize(
            name="iberia", result_warnings=None, exception_keywords=codes
        )
        pytest.fail(
            "Iberia provider raised an exception whose warning_codes contain "
            f"a block signal: {codes}"
        )

    codes = _extract_codes(result.warnings_structured)
    rejected = _block_codes_in(codes)
    assert not rejected, _summarize(name="iberia", result_warnings=rejected, exception_keywords=None)


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.skipif(
    os.getenv("RUN_PROVIDER_SMOKE") not in {"1", "true", "yes", "on"},
    reason="Real network call; opt in via RUN_PROVIDER_SMOKE=1.",
)
def test_easyjet_provider_does_not_get_blocked_by_akamai_or_datadome(smoke_enabled) -> None:
    """Real-network smoke: LGW → BCN on a near-future date.

    Pass = zero flights + clean `provider_empty_result` (no captcha, no
    outage markers).
    Fail = captcha codes, account-wide outage, or any other error.
    """
    assert smoke_enabled, "smoke disabled; gate should have skipped"

    from app.infrastructure.providers.easyjet_provider import EasyJetProvider

    provider = EasyJetProvider()
    try:
        result = provider.get_flights("LGW", "BCN", "2026-08-15", timeout_ms=10000)
    except Exception as exc:
        codes = list(getattr(exc, "warning_codes", []) or [])
        assert not codes, _summarize(
            name="easyjet", result_warnings=None, exception_keywords=codes
        )
        pytest.fail(
            "easyJet provider raised an exception whose warning_codes contain "
            f"a block signal: {codes}"
        )

    codes = _extract_codes(result.warnings_structured)
    rejected = _block_codes_in(codes)
    assert not rejected, _summarize(name="easyjet", result_warnings=rejected, exception_keywords=None)


def test_block_code_classifier_catches_known_signals() -> None:
    """Pure unit assertion: the classifier recognises the codes we care about.

    A regression in this list (typo, removed code, missed fragment) will be
    caught immediately without waiting for the live smoke to fire.
    """
    inputs = [
        "iberia_provider_captcha_akamai_blocked",
        "easyjet_flight_connections_captcha_datadome_captcha",
        "provider_total_outage",
        "iberia_provider_unavailable_total",
        "easyjet_provider_unavailable_total",
    ]
    matched = _block_codes_in(inputs)
    assert matched == inputs, f"classifier dropped codes: got={matched} want={inputs}"

    assert _block_codes_in(["provider_empty_result", "flight_price_unavailable"]) == []
