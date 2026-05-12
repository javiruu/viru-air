from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

import app.api.deps as deps
import app.api.v1.watchlist as watchlist_api
import app.services.alert_service as alert_service
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from app.infrastructure.db.models import User
from app.main import app
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


def _active_quiet_range_utc() -> tuple[str, str]:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).strftime("%H:%M")
    end = (now + timedelta(hours=1)).strftime("%H:%M")
    return start, end


def test_quiet_hours_delay_email_dispatch(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _PriceSequenceProvider([100.0, 90.0]))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="quiet-hours@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _active_quiet_range_utc()

    pref_put = client.put(
        "/api/v1/preferences",
        headers=headers,
        json={
            "default_radius_km": 150,
            "include_stops_default": False,
            "include_nearby_origins_default": False,
            "include_nearby_destinations_default": False,
            "avoid_departure_before": None,
            "depart_before_default": None,
            "strict_filters_default": True,
            "preferred_currency": "EUR",
            "language": "es",
            "quiet_hours_enabled": True,
            "quiet_hours_start": start,
            "quiet_hours_end": end,
            "quiet_hours_timezone": "UTC",
        },
    )
    assert pref_put.status_code == 200

    watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=20)),
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

    _with_admin_override()
    try:
        dispatched = client.post("/api/v1/alerts/dispatch-pending")
        assert dispatched.status_code == 200
    finally:
        app.dependency_overrides.pop(deps.require_admin, None)

    events = client.get(f"/api/v1/alerts/events?watch_id={watch_id}", headers=headers).json()
    by_channel = {event["channel"]: event for event in events}
    assert by_channel["in_app"]["delivery_status"] == "delivered"
    assert by_channel["email"]["delivery_status"] == "queued"
    assert by_channel["email"]["next_attempt_at"] is not None
    assert by_channel["email"]["last_error"] == "quiet_hours_active"


def test_outside_quiet_hours_email_dispatches_normally(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _PriceSequenceProvider([100.0, 90.0]))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="outside-quiet-hours@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    pref_put = client.put(
        "/api/v1/preferences",
        headers=headers,
        json={
            "default_radius_km": 150,
            "include_stops_default": False,
            "include_nearby_origins_default": False,
            "include_nearby_destinations_default": False,
            "avoid_departure_before": None,
            "depart_before_default": None,
            "strict_filters_default": True,
            "preferred_currency": "EUR",
            "language": "es",
            "quiet_hours_enabled": True,
            "quiet_hours_start": "00:00",
            "quiet_hours_end": "00:01",
            "quiet_hours_timezone": "UTC",
        },
    )
    assert pref_put.status_code == 200

    watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=21)),
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
    client.post("/api/v1/alerts/evaluate", headers=headers, json={"watch_id": watch_id})

    _with_admin_override()
    try:
        dispatched = client.post("/api/v1/alerts/dispatch-pending")
        assert dispatched.status_code == 200
    finally:
        app.dependency_overrides.pop(deps.require_admin, None)

    events = client.get(f"/api/v1/alerts/events?watch_id={watch_id}", headers=headers).json()
    by_channel = {event["channel"]: event for event in events}
    assert by_channel["email"]["delivery_status"] == "sent"


def test_alert_events_are_grouped_into_digest_metadata(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(watchlist_api, "provider", _PriceSequenceProvider([100.0, 95.0, 90.0]))
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 0)
    token = register_and_token(client, email="digest-group@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=22)),
            "target_price": 30,
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
            "cooldown_minutes": 1,
        },
    )

    client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    first_eval = client.post("/api/v1/alerts/evaluate", headers=headers, json={"watch_id": watch_id})
    assert first_eval.status_code == 200
    assert first_eval.json()["created"] == 1

    now_future = utc_now_naive() + timedelta(minutes=2)
    monkeypatch.setattr(alert_service, "utc_now", lambda: now_future.replace(tzinfo=UTC))
    client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
    second_eval = client.post("/api/v1/alerts/evaluate", headers=headers, json={"watch_id": watch_id})
    assert second_eval.status_code == 200

    events = client.get(f"/api/v1/alerts/events?watch_id={watch_id}", headers=headers).json()
    first = events[0]
    assert first["is_digest"] is True
    assert first["grouped_count"] >= 2
    assert first["group_reason"] == "every_change"
    assert "Resumen de" in first["message"]
