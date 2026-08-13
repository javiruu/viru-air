from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import requests

from app.hotels import geocoder


class _Response:
    def __init__(self, payload: object, *, status_code: int = 200, content_type: str = "application/json", content_length: str | None = None):
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        if content_length is not None:
            self.headers["Content-Length"] = content_length
        self._body = json.dumps(payload).encode()

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code} api_key=secret-value")

    def iter_content(self, *, chunk_size: int):
        yield self._body

    def close(self) -> None:
        pass


class _SlowResponse(_Response):
    def iter_content(self, *, chunk_size: int):
        yield b"["
        yield b"{\"type\":\"city\",\"lat\":\"40\",\"lon\":\"-3\"},"
        yield b"{\"type\":\"city\",\"lat\":\"41\",\"lon\":\"-4\"}]"


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(geocoder, "is_geocoder_enabled", lambda: True)
    monkeypatch.setattr(geocoder, "_NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    monkeypatch.setattr(geocoder, "_NOMINATIM_ALLOWED_HOSTS", frozenset({"nominatim.openstreetmap.org"}))
    monkeypatch.setattr(geocoder.time, "sleep", lambda _: None)
    monkeypatch.setattr(geocoder.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("8.8.8.8", 443))])


def _session(monkeypatch: pytest.MonkeyPatch, response: _Response) -> MagicMock:
    session = MagicMock()
    session.get.return_value = response
    session.__enter__.return_value = session
    monkeypatch.setattr(geocoder.requests, "Session", lambda: session)
    return session


def test_disabled_geocoder_makes_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(geocoder, "is_geocoder_enabled", lambda: False)
    session = _session(monkeypatch, _Response([]))
    assert geocoder.geocode_city("Madrid") is None
    session.get.assert_not_called()


def test_rejects_non_allowlisted_or_non_https_destination(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    session = _session(monkeypatch, _Response([]))
    for destination in (
        "http://nominatim.openstreetmap.org",
        "https://example.invalid",
        "https://user:pass@nominatim.openstreetmap.org",
        "https://nominatim.openstreetmap.org:8443",
        "https://nominatim.openstreetmap.org/?next=internal",
    ):
        monkeypatch.setattr(geocoder, "_NOMINATIM_URL", destination)
        assert geocoder.geocode_city("Madrid") is None
    session.get.assert_not_called()


def test_rejects_query_that_looks_like_url_or_is_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    session = _session(monkeypatch, _Response([]))
    assert geocoder.geocode_city("https://127.0.0.1/internal") is None
    assert geocoder.geocode_city("x" * 201) is None
    session.get.assert_not_called()


def test_rejects_private_dns_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    monkeypatch.setattr(geocoder.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 443))])
    session = _session(monkeypatch, _Response([]))
    assert geocoder.geocode_city("Madrid") is None
    session.get.assert_not_called()


def test_disables_redirects_and_returns_valid_result(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    response = _Response(
        [{"type": "city", "lat": "40.4168", "lon": "-3.7038", "display_name": "Madrid, Spain", "country_code": "es"}]
    )
    session = _session(monkeypatch, response)
    result = geocoder.geocode_city("Madrid")
    assert result is not None
    assert result["area_label"] == "Madrid"
    assert result["country_code"] == "ES"
    session.get.assert_called_once()
    assert session.get.call_args.kwargs["allow_redirects"] is False
    assert session.get.call_args.kwargs["stream"] is True
    mounted = session.mount.call_args.args
    assert mounted[0] == "https://"
    assert mounted[1]._resolved_ip == "8.8.8.8"
    pool = mounted[1]._pinned_pool
    assert pool is not None
    connection = pool._new_conn()
    assert connection.host == "8.8.8.8"
    assert connection.server_hostname == "nominatim.openstreetmap.org"


def test_rejects_redirects_wrong_content_type_and_oversized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    for response in (
        _Response([], status_code=302),
        _Response([], content_type="text/html"),
        _Response([], content_length=str(geocoder._NOMINATIM_MAX_RESPONSE_BYTES + 1)),
    ):
        session = _session(monkeypatch, response)
        assert geocoder.geocode_city("Madrid") is None
        session.get.assert_called_once()


def test_pinned_connection_applies_deadline_before_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib3.util import Timeout

    connection = geocoder._PinnedHTTPSConnection(
        "ignored",
        resolved_ip="8.8.8.8",
        origin_host="nominatim.openstreetmap.org",
        deadline=100.0,
        timeout=Timeout(connect=10, read=10),
    )
    monkeypatch.setattr(geocoder.time, "monotonic", lambda: 95.0)
    called = []
    monkeypatch.setattr(geocoder.HTTPSConnection, "connect", lambda self: called.append(self.timeout))
    connection.connect()
    assert called == [5.0]


def test_set_response_read_timeout_updates_real_socket_seam() -> None:
    class Socket:
        def __init__(self):
            self.values = []

        def settimeout(self, value):
            self.values.append(value)

    socket = Socket()
    response = MagicMock()
    response.raw._fp.fp.raw._sock = socket
    geocoder._set_response_read_timeout(response, 1.25)
    assert socket.values == [1.25]


def test_stream_reader_enforces_response_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    monkeypatch.setattr(geocoder, "_NOMINATIM_TIMEOUT_SECONDS", 1)
    response = _SlowResponse([])
    session = _session(monkeypatch, response)
    # The socket setter is the transport seam; the loop also checks the clock
    # before consuming each chunk.
    ticks = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(geocoder.time, "monotonic", lambda: next(ticks))
    assert geocoder.geocode_city("Madrid") is None
    session.get.assert_called_once()


def test_malformed_coordinates_are_not_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    session = _session(monkeypatch, _Response([{"type": "city", "lat": "not-a-number", "lon": "-3"}]))
    assert geocoder.geocode_city("Madrid") is None
    session.get.assert_called_once()


def test_error_logs_do_not_include_query_or_secret(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    _enable(monkeypatch)
    session = _session(monkeypatch, _Response([], status_code=500))
    with caplog.at_level("WARNING", logger="app.hotels.geocoder"):
        assert geocoder.geocode_city("Madrid api_key=secret-value") is None
    assert "Madrid" not in caplog.text
    assert "secret-value" not in caplog.text
    assert "api_key=secret-value" not in caplog.text
    session.get.assert_called_once()
