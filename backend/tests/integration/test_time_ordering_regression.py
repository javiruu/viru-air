from __future__ import annotations

from datetime import date, datetime, timedelta

import app.api.v1.watchlist as watchlist_api
from app.domain.entities import ProviderFlight
from fastapi.testclient import TestClient

from tests.helpers import register_and_token


class _SequenceProvider:
    def __init__(self) -> None:
        self._prices = [70.0, 55.0, 48.0]

    def get_flights(self, origin: str, destination: str, travel_date: str) -> list[ProviderFlight]:
        price = self._prices.pop(0) if self._prices else 48.0
        return [
            ProviderFlight(
                price=price,
                currency="EUR",
                departure_time_local="09:15",
                captured_at=watchlist_api.utc_now_naive(),
                source="sequence-provider",
            )
        ]


class _MutableClock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current = self.current + timedelta(seconds=seconds)


def test_history_and_alert_events_keep_descending_order(client: TestClient, monkeypatch) -> None:
    clock = _MutableClock(datetime(2026, 3, 9, 9, 0, 0))
    monkeypatch.setattr(watchlist_api, "provider", _SequenceProvider())
    monkeypatch.setattr(watchlist_api, "REFRESH_COOLDOWN_SECONDS", 60)
    monkeypatch.setattr(watchlist_api, "utc_now_naive", clock.now)

    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_watch = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "travel_date_local": str(date.today() + timedelta(days=14)),
            "target_price": 65,
        },
    )
    assert create_watch.status_code == 200
    watch_id = create_watch.json()["id"]

    create_change_rule = client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "every_change",
            "cooldown_minutes": 1,
        },
    )
    assert create_change_rule.status_code == 200

    create_threshold_rule = client.post(
        "/api/v1/alerts/rules",
        headers=headers,
        json={
            "watch_id": watch_id,
            "rule_type": "threshold_high",
            "threshold_value": 40,
            "cooldown_minutes": 1,
        },
    )
    assert create_threshold_rule.status_code == 200

    for _ in range(3):
        refreshed = client.post(f"/api/v1/watchlist/{watch_id}/refresh-now", headers=headers)
        assert refreshed.status_code == 200
        evaluated = client.post(
            "/api/v1/alerts/evaluate",
            headers=headers,
            json={"watch_id": watch_id},
        )
        assert evaluated.status_code == 200
        clock.advance(61)

    history = client.get(f"/api/v1/prices/history?watch_id={watch_id}", headers=headers)
    assert history.status_code == 200
    history_rows = history.json()
    assert len(history_rows) >= 3
    history_times = [row["captured_at_utc"] for row in history_rows]
    assert history_times == sorted(history_times, reverse=True)

    events = client.get("/api/v1/alerts/events", headers=headers)
    assert events.status_code == 200
    event_rows = events.json()
    assert len(event_rows) >= 2
    event_times = [row["created_at"] for row in event_rows]
    assert event_times == sorted(event_times, reverse=True)
