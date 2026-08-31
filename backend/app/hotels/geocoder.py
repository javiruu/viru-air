"""Optional Nominatim geocoder fallback for area-resolve.

Enabled when HOTEL_GEOCODER_ENABLED=true.
No external API key required — Nominatim is free with usage limits.

The destination is configuration-controlled, never user-controlled. Before a
request we validate the exact HTTPS host and resolve it, rejecting any
non-global address. Redirects are disabled and response bytes are bounded.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import math
import os
import re
import socket
import time
from typing import Any
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPSConnection
from urllib3.connectionpool import HTTPSConnectionPool

from app.hotels.activation import is_hotel_geocoder_enabled

logger = logging.getLogger("app.hotels.geocoder")

_NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org").rstrip("/")
_NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "ViruAir/1.0")
_NOMINATIM_ALLOWED_HOSTS = frozenset(
    host.strip().lower().rstrip(".")
    for host in os.getenv("NOMINATIM_ALLOWED_HOSTS", "nominatim.openstreetmap.org").split(",")
    if host.strip()
)
_NOMINATIM_MAX_QUERY_LENGTH = 200
_NOMINATIM_MAX_RESPONSE_BYTES = max(
    1,
    min(int(os.getenv("HOTEL_GEOCODER_MAX_RESPONSE_BYTES", "262144")), 2 * 1024 * 1024),
)
_NOMINATIM_TIMEOUT_SECONDS = max(
    1,
    min(int(os.getenv("HOTEL_GEOCODER_TIMEOUT_SECONDS", "10")), 30),
)
_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)=?[^&\s,}]+")


def is_geocoder_enabled() -> bool:
    return is_hotel_geocoder_enabled()


def geocode_city(query: str) -> dict[str, object] | None:
    """Resolve a city/area name to coordinates using a validated Nominatim host.

    Returns None on disabled, invalid-input, network, policy, or malformed-
    response outcomes. No exception or provider URL is reflected to callers.
    """
    if not is_geocoder_enabled():
        return None

    try:
        endpoint = _validated_endpoint(_NOMINATIM_URL)
        normalized_query = _validated_query(query)
        resolved_ip = _assert_public_dns(endpoint.hostname or "")
    except (TypeError, ValueError, socket.gaierror, OSError) as exc:
        _log_failure("configuration_or_ssrf_policy", exc)
        return None

    params: dict[str, str] = {
        "q": normalized_query,
        "format": "json",
        "limit": "3",
        "accept-language": "es",
    }

    response: requests.Response | None = None
    session: requests.Session | None = None
    try:
        time.sleep(1.0)  # Rate-limit: 1 req/s for Nominatim free tier
        deadline = time.monotonic() + _NOMINATIM_TIMEOUT_SECONDS
        # Do not inherit a process-wide HTTP proxy for this fixed destination.
        session = requests.Session()
        session.trust_env = False
        session.mount(
            "https://",
            _PinnedHTTPSAdapter(
                resolved_ip=resolved_ip,
                origin_host=endpoint.hostname or "",
                deadline=deadline,
            ),
        )
        response = session.get(
            endpoint.geturl(),
            params=params,
            headers={
                "Host": endpoint.hostname or "",
                "User-Agent": _NOMINATIM_USER_AGENT,
            },
            timeout=_NOMINATIM_TIMEOUT_SECONDS,
            allow_redirects=False,
            stream=True,
        )
        if 300 <= response.status_code < 400:
            raise _GeocoderPolicyError("redirect_not_allowed")
        response.raise_for_status()
        _assert_json_content_type(response.headers.get("Content-Type", ""))
        results = _read_json_response(
            response,
            deadline=deadline,
        )
    except _GeocoderPolicyError as exc:
        _log_failure(str(exc), exc)
        return None
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
        _log_failure("request_or_payload_invalid", exc)
        return None
    finally:
        if response is not None:
            response.close()
        if session is not None:
            session.close()

    if not isinstance(results, list) or not results:
        return None

    try:
        best = _select_best_result(results)
        lat = float(best["lat"])
        lng = float(best["lon"])
        if not math.isfinite(lat) or not math.isfinite(lng) or not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return None
        display_name = str(best.get("display_name") or normalized_query)
        country_code = str(best.get("country_code") or "").upper()
        if len(country_code) > 2:
            country_code = country_code[:2]
    except (KeyError, TypeError, ValueError):
        _log_failure("response_coordinates_invalid", ValueError("invalid_coordinates"))
        return None

    # Extract a short label from display_name (first part before comma).
    area_label = display_name.split(",")[0].strip() or normalized_query
    return {
        "area_label": area_label,
        "latitude": round(lat, 4),
        "longitude": round(lng, 4),
        "country_code": country_code,
        "confidence": "medium",
        "source": "nominatim",
    }


def _validated_endpoint(raw_url: str):
    parsed = urlsplit(raw_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme.lower() != "https"
        or not host
        or host not in _NOMINATIM_ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise _GeocoderPolicyError("destination_not_allowlisted")
    return parsed._replace(scheme="https", netloc=host, path="/search")


def _validated_query(query: str) -> str:
    normalized = str(query or "").strip()
    parsed = urlsplit(normalized)
    if (
        not normalized
        or len(normalized) > _NOMINATIM_MAX_QUERY_LENGTH
        or any(ord(char) < 32 for char in normalized)
        or parsed.scheme
        or parsed.netloc
        or normalized.startswith("//")
    ):
        raise _GeocoderPolicyError("query_not_allowed")
    return normalized


def _assert_public_dns(host: str) -> str:
    addresses = {
        str(info[4][0])
        for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if info[4]
    }
    if not addresses:
        raise _GeocoderPolicyError("destination_dns_empty")
    parsed_addresses = [ipaddress.ip_address(address) for address in addresses]
    for parsed in parsed_addresses:
        if not parsed.is_global:
            raise _GeocoderPolicyError("destination_resolves_private_or_reserved")
    # Pin the connection to one validated address. The hostname remains in the
    # URL and Host header for HTTP semantics and in server_hostname for TLS.
    return sorted(addresses)[0]


def _assert_json_content_type(content_type: str) -> None:
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in {"application/json", "application/geo+json"}:
        raise _GeocoderPolicyError("unexpected_content_type")


def _read_json_response(response: requests.Response, *, deadline: float) -> Any:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > _NOMINATIM_MAX_RESPONSE_BYTES:
                raise _GeocoderPolicyError("response_too_large")
        except ValueError:
            raise _GeocoderPolicyError("invalid_content_length") from None

    chunks: list[bytes] = []
    total = 0
    content_iterator = iter(response.iter_content(chunk_size=16 * 1024))
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _GeocoderPolicyError("response_timeout")
        _set_response_read_timeout(response, remaining)
        try:
            chunk = next(content_iterator)
        except StopIteration:
            break
        if time.monotonic() > deadline:
            raise _GeocoderPolicyError("response_timeout")
        if not chunk:
            continue
        total += len(chunk)
        if total > _NOMINATIM_MAX_RESPONSE_BYTES:
            raise _GeocoderPolicyError("response_too_large")
        chunks.append(chunk)
    return json.loads(b"".join(chunks))


def _set_response_read_timeout(response: requests.Response, remaining: float) -> None:
    """Bound the next blocking urllib3 socket read by the total deadline."""
    raw = getattr(response, "raw", None)
    candidates = (
        getattr(getattr(getattr(raw, "_fp", None), "fp", None), "raw", None),
        getattr(getattr(raw, "_fp", None), "fp", None),
    )
    for stream in candidates:
        sock = getattr(stream, "_sock", None)
        if sock is not None and hasattr(sock, "settimeout"):
            sock.settimeout(max(0.001, remaining))
            return


def _select_best_result(results: list[Any]) -> dict[str, Any]:
    candidates = [item for item in results if isinstance(item, dict)]
    if not candidates:
        raise ValueError("no_mapping_results")
    for result in candidates:
        if result.get("type") in {"city", "administrative"}:
            return result
    return candidates[0]


def _log_failure(reason: str, error: BaseException) -> None:
    # Keep query, URL, headers, and provider exception text out of logs. The
    # stable reason is sufficient for metrics and operational diagnosis.
    logger.warning(
        "nominatim_geocode_failed",
        extra={"reason": reason, "error_type": type(error).__name__},
    )


class _PinnedHTTPSConnection(HTTPSConnection):
    """Connect to a validated IP while retaining origin SNI/certificate host."""

    def __init__(
        self,
        host: str,
        *,
        resolved_ip: str,
        origin_host: str,
        deadline: float,
        **kwargs: Any,
    ) -> None:
        if kwargs.get("server_hostname") is None:
            kwargs["server_hostname"] = origin_host
        if kwargs.get("assert_hostname") is None:
            kwargs["assert_hostname"] = origin_host
        super().__init__(
            host=resolved_ip,
            **kwargs,
        )
        self.origin_host = origin_host
        self._deadline = deadline

    def connect(self) -> None:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("geocoder_response_deadline_exceeded")
        connect_timeout = getattr(self.timeout, "connect_timeout", self.timeout)
        if isinstance(connect_timeout, (int, float)) and not isinstance(connect_timeout, bool):
            self.timeout = max(0.001, min(float(connect_timeout), remaining))
        else:
            self.timeout = max(0.001, remaining)
        super().connect()
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            self.close()
            raise TimeoutError("geocoder_response_deadline_exceeded")
        if self.sock is not None:
            read_timeout = getattr(self.timeout, "read_timeout", self.timeout)
            self.sock.settimeout(max(0.001, min(float(read_timeout), remaining)))


class _PinnedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PinnedHTTPSConnection


class _PinnedHTTPSAdapter(HTTPAdapter):
    def __init__(self, *, resolved_ip: str, origin_host: str, deadline: float) -> None:
        self._resolved_ip = resolved_ip
        self._origin_host = origin_host
        self._deadline = deadline
        self._pinned_pool: _PinnedHTTPSConnectionPool | None = None
        super().__init__(pool_connections=1, pool_maxsize=1, max_retries=0)

    def init_poolmanager(self, connections: int, maxsize: int, block: bool = False, **kwargs: Any) -> None:
        # Keep custom connection metadata out of PoolManager's PoolKey. The
        # fixed pool is selected directly by get_connection below.
        super().init_poolmanager(connections, maxsize, block=block, **kwargs)
        self._pinned_pool = _PinnedHTTPSConnectionPool(
            self._origin_host,
            443,
            maxsize=maxsize,
            block=block,
            retries=0,
            resolved_ip=self._resolved_ip,
            origin_host=self._origin_host,
            deadline=self._deadline,
        )

    def get_connection(self, url: str, proxies: Any = None) -> _PinnedHTTPSConnectionPool:
        if proxies:
            raise _GeocoderPolicyError("proxy_not_allowed")
        if self._pinned_pool is None:
            raise RuntimeError("pinned_geocoder_pool_not_initialized")
        return self._pinned_pool

    def close(self) -> None:
        if self._pinned_pool is not None:
            self._pinned_pool.close()
        super().close()


class _GeocoderPolicyError(ValueError):
    pass
