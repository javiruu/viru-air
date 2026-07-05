"""Operator-driven knobs for the Iberia + easyJet flight provider sessions.

Centralises how each provider builds its curl_cffi session so the operator
can tune Akamai/Datadome bypass behaviour at deploy time without editing
provider code:

- ``IMPERSONATE`` (already supported): the curl_cffi TLS-profile preset.
- ``EXTRA_FP``: a JSON blob of the curl_cffi ``extra_fp`` overrides.
  Used to push TLS / H2 fingerprint knobs the preset doesn't expose
  (``tls_grease``, ``tls_min_version``, ``tls_cipher_order``, H2 frame
  ordering, etc.).
- ``PROXY``: ``http://...`` or ``socks5h://...`` curl_cffi-compatible
  proxy URL. The whole point of this knob: cloud egress IPs get flagged
  by Akamai bot-manager; routing through an unblocked proxy / residential
  IP lets the operator unlock the providers from their own infrastructure
  without code changes.
- ``JA3``: a boolean to force emitting JA3 in the TLS Client Hello (curl_cffi
  ``ja3=True``). Useful for diagnostics.

The factory is intentionally tiny: provider code reads the knobs via
:meth:`build_session_kwargs`, then passes the resulting dict to
``requests.Session(**kwargs)`` exactly as before. The return type is a plain
``dict`` so any future curl_cffi kwarg (``http2``, ``verify``, etc.) lands in
a single place.

Failure mode: bad JSON / bad URL / bad kwarg → log loudly, fall back to the
safe default. We never raise from this factory — the provider runtime keeps
working with whatever it can.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Final

logger = logging.getLogger(__name__)


# Set of known kwarg names we forward to ``curl_cffi.requests.Session``.
# ``extra_fp`` is a TypedDict-shaped dict from curl_cffi, not arbitrary JSON,
# so the factory only forwards keys we recognise. Unknown keys are logged and
# dropped to avoid malformed overrides poisoning the TLS handshake.
_KNOWN_EXTRA_FP_KEYS: Final[frozenset[str]] = frozenset(
    {
        "tls_grease",
        "tls_min_version",
        "tls_max_version",
        "tls_cipher_order",
        "tls_permute_extensions",
        "tls_signature_algorithms",
        "tls_delegated_credential",
        "tls_record_size_limit",
        "h2_stream_priority",
        "h2_stream_weight",
        "h2_initial_window_size",
        "h2_max_header_list_size",
        "pseudo_header_order",
        "connection_flow",
        "header_order",
        "header_priority",
        "enable_ocsp_stapling",
        "disable_compression",
        "alps_protocols",
    }
)


def _read_json_env(name: str) -> dict[str, Any] | None:
    """Parse a ``NAME`` env var as JSON, returning ``None`` on bad input.

    Bad input is logged at INFO so operators can see why their overrides
    silently fall back to defaults, but never raised — provider runtime
    should keep working.
    """
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        import json

        parsed = json.loads(raw)
    except Exception as exc:  # noqa: BLE001 - log + fall back
        logger.info("%s env var is not valid JSON; ignoring (%s)", name, exc)
        return None
    if not isinstance(parsed, dict):
        logger.info("%s env var must be a JSON object; got %r", name, type(parsed).__name__)
        return None
    return parsed


def _filter_extra_fp(raw: dict[str, Any]) -> dict[str, Any]:
    """Drop keys not in ``_KNOWN_EXTRA_FP_KEYS`` so curl_cffi doesn't choke.

    Emits an INFO log per dropped key so operators notice when they typo
    a name instead of silently getting defaults.
    """
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key in _KNOWN_EXTRA_FP_KEYS:
            out[key] = value
        else:
            logger.info("extra_fp key %r not recognised by curl_cffi; dropping", key)
    return out


def build_session_kwargs(
    *,
    impersonate_env: str,
    extra_fp_env: str,
    proxy_env: str,
    ja3_env: str,
) -> dict[str, Any]:
    """Compose the curl_cffi session kwargs from environment overrides.

    Parameters
    ----------
    impersonate_env:
        The name of the env var to read for the impersonate preset
        (e.g. ``IBERIA_IMPERSONATE``).
    extra_fp_env:
        The name of the env var holding the JSON ``extra_fp`` overrides
        (e.g. ``IBERIA_EXTRA_FP``).
    proxy_env:
        The name of the env var holding the proxy URL
        (e.g. ``IBERIA_PROXY``).
    ja3_env:
        The name of the env var controlling the JA3 toggle
        (e.g. ``IBERIA_JA3``).

    Returns
    -------
    A plain dict safe to splat into ``requests.Session(**kwargs)``. Always
    contains ``impersonate`` from one of the provided overrides or the
    default fallback ``chrome131``; ``extra_fp``, ``proxies``, ``ja3`` are
    only included when the operator set them.
    """
    impersonate = (os.getenv(impersonate_env) or "chrome131").strip() or "chrome131"
    kwargs: dict[str, Any] = {"impersonate": impersonate}

    extra_fp_raw = _read_json_env(extra_fp_env)
    if extra_fp_raw:
        kwargs["extra_fp"] = _filter_extra_fp(extra_fp_raw)

    proxy_url = os.getenv(proxy_env)
    if proxy_url:
        proxy_url = proxy_url.strip()
        if proxy_url:
            # curl_cffi accepts a single dict (preferred) or a URL string.
            kwargs["proxies"] = {"http": proxy_url, "https": proxy_url}

    ja3_raw = os.getenv(ja3_env)
    if ja3_raw and ja3_raw.strip().lower() in {"1", "true", "yes", "on"}:
        kwargs["ja3"] = True

    return kwargs
