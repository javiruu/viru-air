"""Standalone Akamai TLS diagnostic for the flight-provider stack.

Walks a list of `curl_cffi` impersonation profiles against an Akamai-protected
edge URL and tabulates the result: HTTP status, server hint, Akamai headers,
and whether the response body looks like a bot-challenge page.

Run directly:
    cd backend && python -m scripts.diagnose_akamai_tls

The diagnostic is intentionally not part of the unit suite; it performs real
network calls. Use it when changing the impersonate version, the header
defaults, or after rotating proxy / egress IP.

**Scope caveat.** The probe is a HEAD request — Akamai's edge logic is biased
on method + payload shape, so a HEAD that returns ``OTHER_404`` / ``OTHER_405``
is NOT proof of a working TLS fingerprint for body-shape-aware endpoints. Use
this to compare impersonation profiles against each other at a TLS layer, not
as a full bypass check. For POST-shape fingerprinting, add a script variant
that POSTs a known payload.
"""

from __future__ import annotations

from collections.abc import Iterable
import logging
import os
import sys

logger = logging.getLogger("diagnose_akamai_tls")

# Ordered list of impersonation profiles to compare. Newer Chrome first,
# keeping `chrome131` (current default) in the middle for easy diffing.
IMPERSONATION_PROFILES: tuple[str, ...] = (
    "chrome131",
    "chrome127",
    "chrome124",
    "chrome120",
    "chrome116",
)


# Default target: ibisservices.iberia.com is the Akamai-protected API edge
# that IberiaProvider hits. Marketing pages on iberia.com are not Akamai-blocked
# at the TLS layer, so probing them gives false confidence. Override with
# `--target URL` (handled in __main__).
DEFAULT_TARGET: str = "https://ibisservices.iberia.com/"


def _classify_response(*, status_code: int | None, headers: dict[str, str], body: str) -> str:
    """Map an HTTP response to a one-word bucket for the table."""
    if status_code is None:
        return "ERR"
    lowered = body.lower()[:1024]
    if status_code == 403:
        if "akamai" in (headers.get("Server") or "").lower() or "akamai" in str(headers).lower():
            return "AKAMAI_BLOCK"
        return "BLOCKED_403"
    if status_code in {301, 302, 303, 307, 308}:
        return f"REDIRECT_{status_code}"
    if "<html" in lowered and ("captcha" in lowered or "challenge" in lowered or "_abck" in lowered):
        return "HTML_CHALLENGE"
    if status_code == 200:
        return "OK"
    return f"OTHER_{status_code}"


def _akamai_hint(headers: dict[str, str]) -> str:
    """Pick the most diagnostic Akamai header if present."""
    for key in ("X-Akamai-Request-ID", "X-Akamai-Cache-Status", "Akamai-Request-BC"):
        value = headers.get(key)
        if value:
            return f"{key}={value}"
    server = headers.get("Server") or ""
    if "Akamai" in server or "AkamaiGHost" in server:
        return f"Server={server}"
    return "-"


def _probe_once(target: str, impersonate: str, *, timeout_s: float = 8.0) -> dict[str, object]:
    """Issue a single HEAD probe and capture status + classification."""
    try:
        from curl_cffi import requests as cc_requests
    except ImportError as exc:
        raise RuntimeError(
            "curl_cffi is required for this diagnostic; install with `uv pip install curl_cffi`."
        ) from exc

    session = cc_requests.Session(impersonate=impersonate)
    try:
        try:
            response = session.head(
                target,
                timeout=timeout_s,
                allow_redirects=False,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                },
            )
            body = response.text or "" if hasattr(response, "text") else ""
        except Exception as exc:
            return {
                "impersonate": impersonate,
                "status": None,
                "bucket": "EXC",
                "akamai": "-",
                "error": f"{type(exc).__name__}: {exc}",
            }
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001 - best effort
            pass

    headers_lower = {k.lower(): v for k, v in dict(response.headers).items()}
    return {
        "impersonate": impersonate,
        "status": response.status_code,
        "bucket": _classify_response(
            status_code=response.status_code,
            headers=headers_lower,
            body=response.text or "",
        ),
        "akamai": _akamai_hint(headers_lower),
        "error": None,
    }


def diagnose(target: str = DEFAULT_TARGET, *, profiles: Iterable[str] = IMPERSONATION_PROFILES) -> list[dict[str, object]]:
    """Run probes for all impersonations and return a list of result rows."""
    rows: list[dict[str, object]] = []
    for profile in profiles:
        logger.info("Probing %s with impersonate=%s", target, profile)
        rows.append(_probe_once(target=target, impersonate=profile))
    return rows


def _render_table(rows: list[dict[str, object]]) -> str:
    headers = ("impersonate", "status", "bucket", "akamai_hint", "error")
    widths = tuple(max(len(str(row.get(h, ""))) for row in ([dict(zip(headers, headers))] + rows)) for h in headers)
    lines = [" | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("-+-".join("-" * w for w in widths))
    for row in rows:
        lines.append(
            " | ".join(str(row.get(h, "") or "").ljust(widths[i]) for i, h in enumerate(headers))
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=os.getenv("DIAGNOSE_AKAMAI_TARGET", DEFAULT_TARGET))
    parser.add_argument("--profile", action="append", default=None, help="Impersonation profile (repeatable).")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(message)s")
    rows = diagnose(target=args.target, profiles=args.profile or IMPERSONATION_PROFILES)
    print(_render_table(rows))
    blockers = [r for r in rows if r["bucket"] in {"AKAMAI_BLOCK", "BLOCKED_403", "HTML_CHALLENGE", "EXC"}]
    if blockers:
        print(
            f"\n{len(blockers)}/{len(rows)} profiles tripped Akamai. "
            "Likely the current chrome131 default needs a header / warmup change.",
            file=sys.stderr,
        )
        return 1
    print(f"\nAll {len(rows)} profiles passed the basic TLS probe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
