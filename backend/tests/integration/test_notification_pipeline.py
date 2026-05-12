from datetime import date, timedelta

from fastapi.testclient import TestClient

import app.api.deps as deps
import app.api.v1.watchlist as watchlist_api
import app.services.notification_service as notification_service
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from app.main import app
from app.infrastructure.db.models import User
from tests.helpers import register_and_token


class _PriceSequenceProvider:
    def __init__(self, prices: list[float]) -> None:
        self._prices = prices
        self._index = 0

    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        value = self._prices[min(self._index, len(self._prices) - 1)]
        self._index += 1
        return [
            ProviderFlight(
                price=value,
                currency="EUR",
                departure_time_local="09:00",
                captured_at=utc_now_naive(),
                source="sequence-provider",
            )
        ]


def _with_admin_override() -> None:
    app.dependency_overrides[deps.require_admin] = lambda: User(
        id="admin-test",
        email="admin@viru.dev",
        password_hash="-",
        is_admin=True,
        locale="es",
        timezone="Europe/Madrid",
    )


def test_dispatch_pending_delivers_in_app_events(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _PriceSequenceProvider([100.0, 94.0]))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="notify-inapp@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=15)),
            "target_price": 35,
        },
    ).json()
    watch_id = watch["id"]
    client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "every_change",
            "notify_on_every_change": False,
            "cooldown_minutes": 60,
        },
    )
    client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    evaluated = client.post("/api/v1/alerts/evaluate", headers=headers, json={"watch_id": watch_id})
    assert evaluated.status_code == 200
    assert evaluated.json()["created"] == 1

    _with_admin_override()
    try:
        dispatched = client.post("/api/v1/alerts/dispatch-pending")
        assert dispatched.status_code == 200
        assert dispatched.json()["processed"] >= 1
        assert dispatched.json()["delivered"] >= 1
    finally:
        app.dependency_overrides.pop(deps.require_admin, None)

    events = client.get(f"/api/v1/alerts/events?watch_id={watch_id}", headers=headers)
    first = events.json()[0]
    assert first["delivery_status"] == "delivered"
    assert first["attempts"] == 1
    assert first["delivered_at"] is not None


def test_dispatch_pending_handles_email_stub_and_retries_on_failure(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _PriceSequenceProvider([100.0, 90.0]))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="notify-email@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=16)),
            "target_price": 30,
        },
    ).json()
    watch_id = watch["id"]
    client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "threshold_low",
            "threshold_value": 95,
            "notify_on_every_change": True,
            "cooldown_minutes": 60,
        },
    )
    client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    evaluate = client.post("/api/v1/alerts/evaluate", headers=headers, json={"watch_id": watch_id})
    assert evaluate.status_code == 200
    assert evaluate.json()["created"] == 2

    def _always_fail(self, event):  # noqa: ANN001
        if event.channel == "email":
            return False, "forced_test_failure"
        return True, None

    monkeypatch.setattr(notification_service.EmailNotificationAdapter, "send", _always_fail)
    monkeypatch.setattr(notification_service, "_next_attempt_delay", lambda attempts: timedelta(seconds=0))

    _with_admin_override()
    try:
        first_dispatch = client.post("/api/v1/alerts/dispatch-pending")
        assert first_dispatch.status_code == 200
        assert first_dispatch.json()["retried"] >= 1

        second_dispatch = client.post("/api/v1/alerts/dispatch-pending")
        assert second_dispatch.status_code == 200

        third_dispatch = client.post("/api/v1/alerts/dispatch-pending")
        assert third_dispatch.status_code == 200
        assert third_dispatch.json()["failed"] >= 1 or third_dispatch.json()["skipped"] >= 1
    finally:
        app.dependency_overrides.pop(deps.require_admin, None)

    events = client.get(f"/api/v1/alerts/events?watch_id={watch_id}", headers=headers).json()
    channels = {event["channel"]: event for event in events}
    assert channels["in_app"]["delivery_status"] == "delivered"
    assert channels["email"]["attempts"] >= 3
    assert channels["email"]["delivery_status"] == "failed"
    assert channels["email"]["last_error"] == "forced_test_failure"
