from __future__ import annotations

import socket
from typing import Final, Literal

import httpx2

_OVERPASS_ENDPOINT: Final = "https://overpass-api.de/api/interpreter"
_MAX_RESPONSE_BYTES: Final = 512 * 1024


class OverpassRequestError(Exception):
    def __init__(
        self,
        error_code: Literal["rate_limited", "timeout", "invalid_response", "provider_unavailable"],
    ) -> None:
        self.error_code = error_code
        super().__init__(error_code)


class HttpxOverpassTransport:
    def fetch(self, *, query: str, user_agent: str) -> bytes:
        limits = httpx2.Limits(
            max_connections=1,
            max_keepalive_connections=1,
            keepalive_expiry=30.0,
        )
        timeout = httpx2.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
        transport = httpx2.HTTPTransport(
            http2=True,
            retries=0,
            limits=limits,
            socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
            trust_env=False,
        )
        try:
            with httpx2.Client(
                transport=transport,
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                with client.stream(
                    "POST",
                    _OVERPASS_ENDPOINT,
                    content=query.encode("utf-8"),
                    headers={"Accept": "application/json", "User-Agent": user_agent},
                ) as response:
                    _raise_for_disallowed_response(response)
                    return _read_response_bytes(response)
        except httpx2.TimeoutException as exc:
            raise OverpassRequestError("timeout") from exc
        except httpx2.HTTPError as exc:
            raise OverpassRequestError("provider_unavailable") from exc


def _raise_for_disallowed_response(response: httpx2.Response) -> None:
    if response.status_code == 429:
        raise OverpassRequestError("rate_limited")
    if response.status_code < 200 or response.status_code >= 300:
        raise OverpassRequestError("provider_unavailable")
    content_type = response.headers.get("Content-Type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise OverpassRequestError("invalid_response")


def _read_response_bytes(response: httpx2.Response) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > _MAX_RESPONSE_BYTES:
                raise OverpassRequestError("invalid_response")
        except ValueError as exc:
            raise OverpassRequestError("invalid_response") from exc
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > _MAX_RESPONSE_BYTES:
            raise OverpassRequestError("invalid_response")
        chunks.append(chunk)
    return b"".join(chunks)
