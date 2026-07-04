import datetime as dt
from types import SimpleNamespace

from app.services.watchlist_refresh_policy import evaluate_route_freshness


def test_evaluate_route_freshness_marks_missing_snapshot() -> None:
    watch = SimpleNamespace(id="watch-1")

    result = evaluate_route_freshness(
        watches=[watch],
        latest_snapshot_by_watch={},
        now=dt.datetime(2026, 6, 21, 12, 0, 0),
        max_age_seconds=86_400,
    )

    assert result.state == "missing_snapshot"
    assert result.needs_refresh is True
    assert result.oldest_snapshot_age_seconds is None


def test_evaluate_route_freshness_marks_expired_and_fresh_routes() -> None:
    watch = SimpleNamespace(id="watch-1")
    expired_snapshot = SimpleNamespace(captured_at_utc=dt.datetime(2026, 6, 18, 12, 0, 0))
    fresh_snapshot = SimpleNamespace(captured_at_utc=dt.datetime(2026, 6, 21, 11, 0, 0))
    now = dt.datetime(2026, 6, 21, 12, 0, 0)

    expired = evaluate_route_freshness(
        watches=[watch],
        latest_snapshot_by_watch={watch.id: expired_snapshot},
        now=now,
        max_age_seconds=86_400,
    )
    fresh = evaluate_route_freshness(
        watches=[watch],
        latest_snapshot_by_watch={watch.id: fresh_snapshot},
        now=now,
        max_age_seconds=86_400,
    )

    assert expired.state == "snapshot_expired"
    assert expired.needs_refresh is True
    assert expired.oldest_snapshot_age_seconds == 259200
    assert fresh.state == "fresh"
    assert fresh.needs_refresh is False
    assert fresh.oldest_snapshot_age_seconds == 3600


def test_evaluate_route_freshness_expires_at_four_hours() -> None:
    watch = SimpleNamespace(id="watch-1")
    snapshot = SimpleNamespace(captured_at_utc=dt.datetime(2026, 6, 21, 8, 0, 0))

    result = evaluate_route_freshness(
        watches=[watch],
        latest_snapshot_by_watch={watch.id: snapshot},
        now=dt.datetime(2026, 6, 21, 12, 0, 0),
        max_age_seconds=14_400,
    )

    assert result.state == "snapshot_expired"
    assert result.needs_refresh is True
    assert result.oldest_snapshot_age_seconds == 14_400
