"""Direct tests for the shared captcha / WAF detection helper.

These tests pin the helper's contract: empty rules are rejected, ordering wins,
faulty predicates don't poison the sweep, and both providers' rule sets are
still wired to emit the expected labels.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.domain.entities import ProviderSourceFetchError
from app.infrastructure.providers._captcha import WafRule, detect_captcha_kind


class _FakeResponse:
    def __init__(self, *, status_code: int | None = 200, text: str | None = None) -> None:
        self.status_code = status_code
        self._text = text

    @property
    def text(self) -> str | None:
        if self._text is None:
            raise RuntimeError("decode failed")
        return self._text


def test_detect_captcha_kind_returns_none_for_clean_response() -> None:
    rules: dict[str, WafRule] = {
        "captcha": lambda status, text: status == 403 and "captcha" in text,
    }
    response = _FakeResponse(status_code=200, text='{"flights": []}')
    assert detect_captcha_kind(response, rules=rules) is None


def test_detect_captcha_kind_matches_first_rule() -> None:
    rules: dict[str, WafRule] = {
        "akamai_captcha": lambda status, text: status == 403 and "captcha" in text,
        "akamai_blocked": lambda status, text: status == 403,
    }
    response = _FakeResponse(status_code=403, text="Please solve the captcha")
    assert detect_captcha_kind(response, rules=rules) == "akamai_captcha"


def test_detect_captcha_kind_honours_rule_order() -> None:
    """Order matters: the more specific kind must come before the generic one."""
    # Reverse the order from the test above to prove the sweep stops at the
    # first hit when the more-specific comes second.
    rules: dict[str, WafRule] = {
        "akamai_blocked": lambda status, text: status == 403,
        "akamai_captcha": lambda status, text: status == 403 and "captcha" in text,
    }
    response = _FakeResponse(status_code=403, text="Please solve the captcha")
    assert detect_captcha_kind(response, rules=rules) == "akamai_blocked"


def test_detect_captcha_kind_skips_faulty_predicate_and_keeps_sweep() -> None:
    def boom(status: int | None, text: str) -> bool:
        raise RuntimeError("predicate crashed")

    rules: dict[str, WafRule] = {
        "faulty": boom,
        "captcha": lambda status, text: status == 403 and "captcha" in text,
    }
    response = _FakeResponse(status_code=403, text="captcha required")
    assert detect_captcha_kind(response, rules=rules) == "captcha"


def test_detect_captcha_kind_tolerates_text_decode_failure() -> None:
    """A response that can't decode its body must still allow status-driven rules."""
    rules: dict[str, WafRule] = {
        "akamai_blocked": lambda status, text: status == 403,
    }
    response = _FakeResponse(status_code=403, text=None)  # raises on .text
    assert detect_captcha_kind(response, rules=rules) == "akamai_blocked"


def test_detect_captcha_kind_handles_missing_attributes_gracefully() -> None:
    """Duck typing: response may not have `text` or `status_code` at all."""

    class Bare:
        pass

    rules: dict[str, WafRule] = {
        "captcha": lambda status, text: status == 403 and "captcha" in text,
        "blocked": lambda status, text: status == 403,
    }
    bare = Bare()
    # No status_code -> None, no text -> empty string. No rule fires.
    assert detect_captcha_kind(bare, rules=rules) is None


def test_detect_captcha_kind_rejects_empty_rules() -> None:
    response = _FakeResponse(status_code=403, text="captcha")
    with pytest.raises(ValueError):
        detect_captcha_kind(response, rules={})


def test_detect_captcha_kind_waf_rules_for_iberia_label_expected_kinds() -> None:
    """The Iberia ruleset is still wired and still emits the expected labels.

    If a future tweak to the helper makes the rules unreachable, this test
    catches it before production does.
    """
    from app.infrastructure.providers.iberia_provider import _IBERIA_WAF_RULES

    response = _FakeResponse(status_code=403, text='<meta http-equiv="refresh"> captcha')
    assert detect_captcha_kind(response, rules=_IBERIA_WAF_RULES) == "akamai_captcha"

    response = _FakeResponse(status_code=403, text="Akamai _abck sensor required")
    assert detect_captcha_kind(response, rules=_IBERIA_WAF_RULES) == "akamai_captcha"

    response = _FakeResponse(status_code=403, text="Access denied. Request rejected.")
    assert detect_captcha_kind(response, rules=_IBERIA_WAF_RULES) == "akamai_blocked"

    response = _FakeResponse(status_code=200, text='{"flights": []}')
    assert detect_captcha_kind(response, rules=_IBERIA_WAF_RULES) is None


def test_detect_captcha_kind_waf_rules_for_easyjet_label_expected_kinds() -> None:
    from app.infrastructure.providers.easyjet_provider import _EASYJET_WAF_RULES

    response = _FakeResponse(status_code=403, text="dd_block dd_4=1 datadome cookies missing")
    assert detect_captcha_kind(response, rules=_EASYJET_WAF_RULES) == "datadome_captcha"

    response = _FakeResponse(
        status_code=200,
        text="<html><script>var dd=...</script>please solve the captcha</html>",
    )
    assert detect_captcha_kind(response, rules=_EASYJET_WAF_RULES) == "datadome_captcha"

    response = _FakeResponse(status_code=403, text="Access denied by edge")
    assert detect_captcha_kind(response, rules=_EASYJET_WAF_RULES) == "akamai_blocked"

    response = _FakeResponse(status_code=200, text="{}")
    assert detect_captcha_kind(response, rules=_EASYJET_WAF_RULES) is None


def test_iberia_provider_raises_canonical_outage_with_captcha_meta_on_403() -> None:
    """End-to-end: a captcha-shaped 403 surfaces as ProviderSourceFetchError
    with the expected warning_codes and meta.reason. Locks in the contract
    between provider, helper, and orchestrator-facing warning catalogue.
    """
    from app.infrastructure.providers.iberia_provider import IberiaProvider

    class _CaptchaSession:
        def post(self, *args: Any, **kwargs: Any) -> _FakeResponse:
            # "Access denied" without "captcha" makes the specific kind
            # akamai_blocked (not akamai_captcha), so the full warning code
            # string is unambiguous.
            return _FakeResponse(
                status_code=403,
                text="Access denied. Request rejected by edge.",
            )

    provider = IberiaProvider(
        api_base_url="https://api.example.test",
        base_url="https://www.iberia.example.test",
        authorization="Basic t",
        market="ES",
        language="es",
    )
    # Duck-typed skip via `getattr(self._session, "get", None) is None`
    # already short-circuits the warmup because this fake only exposes `post`.
    provider._session = _CaptchaSession()  # type: ignore[assignment]

    with pytest.raises(ProviderSourceFetchError) as exc:
        provider.get_flights("MAD", "JFK", "2026-06-14")

    assert exc.value.provider_id == "iberia"
    assert "iberia_provider_captcha_akamai_blocked" in exc.value.warning_codes
    assert exc.value.meta == {"reason": "akamai_blocked"}
