import os
import tempfile
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from app.infrastructure.db.models import NotificationEvent
from app.infrastructure.db.session import Base
from app.main import app
from app.worker import notifications as notification_worker
from tests.helpers import register_and_token
import app.api.deps as deps
from app.infrastructure.db.models import User


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


@pytest.fixture()
def worker_client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_db_url = f"sqlite:///{path}"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.api.v1.watchlist.provider", _PriceSequenceProvider([100.0, 90.0]))
    monkeypatch.setattr("app.api.v1.watchlist.REFRESH_COOLDOWN_SECONDS", 0)

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()
    engine.dispose()
    try:
        os.remove(path)
    except PermissionError:
        pass


def _create_alert_events(client: TestClient, *, email: str) -> str:
    token = register_and_token(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=25)),
            "target_price": 35,
        },
    )
    watch_id = watch.json()["id"]
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
    return watch_id


def _active_quiet_range_utc() -> tuple[str, str]:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=1)).strftime("%H:%M")
    end = (now + timedelta(hours=1)).strftime("%H:%M")
    return start, end


def _with_admin_override() -> None:
    app.dependency_overrides[deps.require_admin] = lambda: User(
        id="admin-test",
        email="admin@viru.dev",
        password_hash="-",
        is_admin=True,
        locale="es",
        timezone="Europe/Madrid",
    )


def test_worker_once_processes_pending_events(worker_client) -> None:
    client, session_factory = worker_client
    watch_id = _create_alert_events(client, email="worker-once@viru.dev")

    result = notification_worker.run_once(session_factory=session_factory, limit=50)
    assert result.processed >= 2
    assert result.delivered >= 2

    with session_factory() as db:
        events = list(
            db.scalars(
                select(NotificationEvent).where(NotificationEvent.delivery_status.in_(("delivered", "sent")))
            )
        )
    assert len(events) >= 2

    token = register_and_token(client, email="worker-once@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    listed = client.get(f"/api/v1/alerts/events?watch_id={watch_id}", headers=headers)
    assert listed.status_code == 200


def test_worker_respects_future_next_attempt_at(worker_client) -> None:
    client, session_factory = worker_client
    _create_alert_events(client, email="worker-next-at@viru.dev")

    with session_factory() as db:
        email_event = db.scalar(
            select(NotificationEvent).where(NotificationEvent.channel == "email").order_by(NotificationEvent.created_at.desc())
        )
        assert email_event is not None
        email_event.delivery_status = "failed"
        email_event.next_attempt_at = utc_now_naive() + timedelta(hours=1)
        email_event.attempts = 1
        db.commit()

    result = notification_worker.run_once(session_factory=session_factory, limit=50)
    assert result.processed >= 1

    with session_factory() as db:
        email_event_after = db.scalar(
            select(NotificationEvent).where(NotificationEvent.channel == "email").order_by(NotificationEvent.created_at.desc())
        )
        assert email_event_after is not None
        assert email_event_after.delivery_status == "failed"
        assert email_event_after.attempts == 1


def test_worker_respects_quiet_hours(worker_client) -> None:
    client, session_factory = worker_client
    token = register_and_token(client, email="worker-quiet@viru.dev")
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
    _create_alert_events(client, email="worker-quiet@viru.dev")

    result = notification_worker.run_once(session_factory=session_factory, limit=50)
    assert result.processed >= 2

    with session_factory() as db:
        email_event = db.scalar(
            select(NotificationEvent).where(NotificationEvent.channel == "email").order_by(NotificationEvent.created_at.desc())
        )
        assert email_event is not None
        assert email_event.delivery_status == "queued"
        assert email_event.next_attempt_at is not None


def test_dispatch_pending_endpoint_still_operates(worker_client) -> None:
    client, _ = worker_client
    _create_alert_events(client, email="worker-dispatch-endpoint@viru.dev")
    _with_admin_override()
    try:
        response = client.post("/api/v1/alerts/dispatch-pending")
        assert response.status_code == 200
        assert "processed" in response.json()
    finally:
        app.dependency_overrides.pop(deps.require_admin, None)
