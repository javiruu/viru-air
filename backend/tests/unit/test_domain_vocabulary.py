from app.domain.vocabulary import (
    DELIVERY_STATUS_VALUES,
    SYSTEM_STATUS_VALUES,
    WATCH_STATUS_VALUES,
)


def test_watch_statuses_are_canonical():
    assert WATCH_STATUS_VALUES == ("active", "paused", "deleted")


def test_delivery_statuses_are_canonical():
    assert DELIVERY_STATUS_VALUES == ("queued", "sent", "delivered", "failed", "error")


def test_system_statuses_are_canonical():
    assert SYSTEM_STATUS_VALUES == ("ok", "degraded", "critical")
