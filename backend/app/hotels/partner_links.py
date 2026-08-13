"""Validation for external hotel partner links.

A provider URL is untrusted data. Hotel links are deny-by-default until an
operator explicitly registers approved hosts and query keys. This module never
fetches or follows a link; it only returns a safe normalized URL for a CTA.
"""
from __future__ import annotations

import ipaddress
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "email",
    "password",
    "secret",
    "token",
    "tracking",
    "user",
    "rule",
)


def sanitize_hotel_deep_link(url: str | None, *, provider: str | None = None) -> str | None:
    """Return an approved external HTTPS link or ``None``.

    Hosts and query keys are configured explicitly. Provider is reserved for
    future provider-specific policies and is intentionally not trusted as an
    allowlist by itself.
    """
    if not url or any(ord(char) < 32 or ord(char) == 127 for char in url):
        return None
    # Browsers treat backslashes as separators in special URLs. Reject them
    # rather than allowing parser/browser disagreement around the destination.
    if "\\" in url:
        return None
    allowed_hosts = _csv_env("HOTEL_DEEPLINK_ALLOWED_HOSTS")
    allowed_query_keys = _csv_env("HOTEL_DEEPLINK_ALLOWED_QUERY_KEYS")
    if not allowed_hosts:
        return None

    try:
        parsed = urlsplit(url.strip())
        host = parsed.hostname
        if not host:
            return None
        normalized_host = host.lower().rstrip(".")
        if normalized_host not in allowed_hosts:
            return None
        if any(ord(char) > 127 for char in normalized_host):
            return None
        path = parsed.path or "/"
        if (
            parsed.scheme.lower() != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or parsed.fragment
            or path.startswith("//")
            or not path.startswith("/")
        ):
            return None
        try:
            if ipaddress.ip_address(normalized_host):
                # Hosts are intentionally domain-only. This also prevents an
                # operator mistake from turning the allowlist into an SSRF
                # exception for loopback/private/link-local IPs.
                return None
        except ValueError:
            pass
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        if any(
            key.lower() not in allowed_query_keys
            or _is_sensitive_key(key)
            or any(ord(char) < 32 or ord(char) == 127 for char in key + value)
            for key, value in pairs
        ):
            return None
        clean_query = urlencode(pairs, doseq=True)
        return urlunsplit(("https", normalized_host, path, clean_query, ""))
    except (TypeError, ValueError):
        return None


def _csv_env(name: str) -> frozenset[str]:
    return frozenset(
        value.strip().lower().rstrip(".")
        for value in os.getenv(name, "").split(",")
        if value.strip()
    )


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)
