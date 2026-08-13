from unittest.mock import MagicMock, patch

import pytest
import requests

from app.core.request_context import (
    reset_client_event_id,
    reset_correlation_id,
    set_client_event_id,
    set_correlation_id,
)
from app.hotels.makcorps_provider import (
    MakcorpsHotelProviderAdapter,
    _build_session,
    _redact_provider_payload,
    _redact_sensitive_text,
)
from app.hotels.partner_links import sanitize_hotel_deep_link


def test_deep_link_is_denied_without_explicit_host_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOTEL_DEEPLINK_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_QUERY_KEYS", "")

    assert sanitize_hotel_deep_link("https://booking.example/hotel/123") is None


def test_deep_link_accepts_only_normalized_https_allowlisted_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_HOSTS", "booking.example")
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_QUERY_KEYS", "checkin,checkout")

    assert (
        sanitize_hotel_deep_link(
            " HTTPS://BOOKING.EXAMPLE/hotel/123?checkout=2026-08-03&checkin=2026-08-01#fragment "
        )
        is None
    )
    assert sanitize_hotel_deep_link(
        "https://BOOKING.EXAMPLE/hotel/123?checkout=2026-08-03&checkin=2026-08-01"
    ) == "https://booking.example/hotel/123?checkout=2026-08-03&checkin=2026-08-01"


def test_deep_link_rejects_schemes_userinfo_ports_fragments_and_path_authority_confusion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_HOSTS", "booking.example")
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_QUERY_KEYS", "")

    rejected = (
        "javascript:alert(1)",
        "http://booking.example/hotel/123",
        "https://user:pass@booking.example/hotel/123",
        "https://booking.example:8443/hotel/123",
        "https://booking.example//attacker.example",
        "https://booking.example/hotel/123\\\\@attacker.example",
        "https://127.0.0.1/hotel/123",
        "https://[::1]/hotel/123",
    )
    for url in rejected:
        assert sanitize_hotel_deep_link(url) is None, url


def test_deep_link_rejects_sensitive_or_unapproved_query_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_HOSTS", "booking.example")
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_QUERY_KEYS", "checkin,token")

    assert sanitize_hotel_deep_link("https://booking.example/hotel/123?token=secret") is None
    assert sanitize_hotel_deep_link("https://booking.example/hotel/123?token") is None
    assert sanitize_hotel_deep_link("https://booking.example/hotel/123?utm_source=viru") is None
    assert sanitize_hotel_deep_link("https://booking.example/hotel/123?unknown=value") is None


def test_deep_link_is_sanitized_at_orm_persistence_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import date

    from app.infrastructure.db.models import Base, HotelProperty, HotelRateSnapshot
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    monkeypatch.delenv("HOTEL_DEEPLINK_ALLOWED_HOSTS", raising=False)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    try:
        with Session(engine) as db:
            hotel = HotelProperty(
                canonical_name="Hotel",
                normalized_name="hotel",
                city="Madrid",
                country_code="ES",
            )
            db.add(hotel)
            db.flush()
            snapshot = HotelRateSnapshot(
                hotel_id=hotel.id,
                provider="makcorps",
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=100,
                deep_link="https://evil.example/redirect?token=secret",
            )
            db.add(snapshot)
            db.commit()
            assert snapshot.deep_link is None
    finally:
        engine.dispose()


def test_makcorps_redacts_url_query_secrets_from_exception_text() -> None:
    secret = "sk-secret-never-log"
    message = f'HTTPSConnectionPool(host="api.makcorps.com"): GET https://api.makcorps.com/hotel?api_key={secret}&hotelid=123 failed'

    redacted = _redact_sensitive_text(message)

    assert secret not in redacted
    assert "api_key=***" in redacted


def test_makcorps_redacts_nested_provider_payload_secrets() -> None:
    payload = {
        "next": "https://api.makcorps.com/city?api_key=secret-value",
        "metadata": {"Authorization": "Bearer secret-token"},
        "hotelId": "mk-1",
    }

    redacted = _redact_provider_payload(payload)

    assert redacted["next"] == "https://api.makcorps.com/city?api_key=***"
    assert redacted["metadata"]["Authorization"] == "***"
    assert redacted["hotelId"] == "mk-1"


def test_makcorps_session_carries_request_context_headers() -> None:
    correlation_token = set_correlation_id("corr-makcorps-test")
    event_token = set_client_event_id("intent-makcorps-test")
    try:
        session = _build_session()
        assert session.headers["x-correlation-id"] == "corr-makcorps-test"
        assert session.headers["x-client-event-id"] == "intent-makcorps-test"
    finally:
        reset_client_event_id(event_token)
        reset_correlation_id(correlation_token)


def test_makcorps_session_serializes_shared_requests() -> None:
    import threading
    import time

    session = MagicMock(spec=requests.Session)
    active = {"count": 0, "max": 0}
    guard = threading.Lock()

    def get_with_overlap_guard(*args, **kwargs):
        with guard:
            active["count"] += 1
            active["max"] = max(active["max"], active["count"])
        time.sleep(0.01)
        with guard:
            active["count"] -= 1
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = []
        return response

    session.get.side_effect = get_with_overlap_guard
    adapter = MakcorpsHotelProviderAdapter(session=session)
    threads = [threading.Thread(target=adapter._get, args=("/mapping", {"name": str(i)})) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert active["max"] == 1


def test_makcorps_http_exception_does_not_log_api_key(caplog: pytest.LogCaptureFixture) -> None:
    secret = "sk-secret-never-log"
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = requests.exceptions.ConnectionError(
        f"GET https://api.makcorps.com/hotel?api_key={secret}&hotelid=123"
    )

    with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", secret):
        adapter = MakcorpsHotelProviderAdapter(session=session)
        assert adapter._get("/hotel", {"hotelid": "123"}) is None

    assert secret not in caplog.text
    assert "api_key=***" in caplog.text
