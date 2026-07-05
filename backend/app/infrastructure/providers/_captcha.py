"""Shared WAF bot challenge detection for flight providers.

Each provider feeds in a dict of rules — a kind label mapped to a predicate
over `(status_code, lowered_body_text)`. The first matching rule wins.

The function reads `status_code` and `text` from the response via `getattr`, so
it works equally well on `requests.Response` and `curl_cffi.Response` without
binding the providers to either library.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

# A rule receives (status_code, lowered_response_text) and returns True if the
# response looks like a WAF bot challenge of the registered kind.
WafRule = Callable[[int | None, str], bool]

_ANY_RULES_HINT: Final = "rules arg must be a dict[str, predicate]"


def detect_captcha_kind(response: Any, *, rules: dict[str, WafRule]) -> str | None:
    """Return the first matching challenge kind, or None if the response is clean.

    Order matters: callers should place the most specific kinds (e.g. captcha)
    before generic ban pages (e.g. akamai_blocked), otherwise a generic deny
    would shadow the richer signal.
    """
    if not rules:
        raise ValueError(_ANY_RULES_HINT)
    status = getattr(response, "status_code", None)
    try:
        lowered = (response.text or "").lower()
    except Exception:
        # If `.text` itself blows up (e.g. chunked decode failure), still allow
        # status-only rules to fire with an empty body.
        lowered = ""
    for kind, predicate in rules.items():
        try:
            if predicate(status, lowered):
                return kind
        except Exception:
            # A faulty predicate should not poison the whole sweep; let the
            # next rule try.
            continue
    return None
