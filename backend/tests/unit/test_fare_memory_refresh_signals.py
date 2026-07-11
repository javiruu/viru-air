import datetime as dt
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.vocabulary import WATCH_STATUS_ACTIVE
from app.infrastructure.db.models import (
    AlertRule,
    Base,
    FlightWatch,
    QuickSearchPopularityCounter,
    User,
)
from app.services.fare_memory_observability import build_fare_memory_health_snapshot
from app.services.fare_memory_refresh_signals import build_route_refresh_signals


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.flush()
    return user


def test_build_route_refresh_signals_prioritizes_product_interest(db: Session) -> None:
    now = dt.datetime(2026, 6, 16, 10, 0)
    user_one = _seed_user(db, "route-signal-one@example.com")
    user_two = _seed_user(db, "route-signal-two@example.com")
    user_three = _seed_user(db, "route-signal-three@example.com")

    watch_one = FlightWatch(
        user_id=user_one.id,
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date_local=dt.date(2026, 6, 20),
        status=WATCH_STATUS_ACTIVE,
    )
    watch_two = FlightWatch(
        user_id=user_two.id,
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date_local=dt.date(2026, 6, 20),
        status=WATCH_STATUS_ACTIVE,
    )
    inactive_watch = FlightWatch(
        user_id=user_three.id,
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date_local=dt.date(2026, 6, 20),
        status="paused",
    )
    competing_watch = FlightWatch(
        user_id=user_one.id,
        origin_iata="AGP",
        destination_iata="FCO",
        travel_date_local=dt.date(2026, 7, 4),
        status=WATCH_STATUS_ACTIVE,
    )
    db.add_all([watch_one, watch_two, inactive_watch, competing_watch])
    db.flush()
    db.add(AlertRule(watch_id=watch_one.id, rule_type="price_below", threshold_value=99, enabled=True))
    db.add(AlertRule(watch_id=watch_two.id, rule_type="price_below", threshold_value=95, enabled=False))
    db.add(
        QuickSearchPopularityCounter(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 20),
            currency="EUR",
            search_count=7,
            first_searched_at=now - dt.timedelta(days=2),
            last_searched_at=now - dt.timedelta(hours=2),
        )
    )
    db.add(
        QuickSearchPopularityCounter(
            origin_iata="AGP",
            destination_iata="FCO",
            travel_date=dt.date(2026, 7, 4),
            currency="EUR",
            search_count=2,
            first_searched_at=now - dt.timedelta(days=1),
            last_searched_at=now - dt.timedelta(hours=3),
        )
    )
    db.add(
        QuickSearchPopularityCounter(
            origin_iata="MAD",
            destination_iata="ORY",
            travel_date=dt.date(2026, 6, 10),
            currency="EUR",
            search_count=100,
            first_searched_at=now - dt.timedelta(days=1),
            last_searched_at=now - dt.timedelta(hours=1),
        )
    )
    db.commit()

    signals = build_route_refresh_signals(db, now=now, limit=10)

    assert [signal.route for signal in signals] == ["LEI-DUB", "AGP-FCO"]
    strongest = signals[0]
    assert strongest.active_watch_count == 2
    assert strongest.enabled_alert_count == 1
    assert strongest.recent_search_count == 7
    assert strongest.days_until_departure == 4
    assert strongest.priority_score > signals[1].priority_score
    assert strongest.suggested_job_priority < signals[1].suggested_job_priority
    assert strongest.reasons == (
        "active_watchlist",
        "enabled_alerts",
        "recent_searches",
        "departure_near",
    )
    assert "user_id" not in str(strongest)


def test_health_snapshot_exposes_refresh_signals_without_personal_data(db: Session) -> None:
    now = dt.datetime(2026, 6, 16, 10, 0)
    user = _seed_user(db, "health-refresh-signal@example.com")
    watch = FlightWatch(
        user_id=user.id,
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date_local=dt.date(2026, 6, 19),
        status=WATCH_STATUS_ACTIVE,
    )
    db.add(watch)
    db.flush()
    db.add(AlertRule(watch_id=watch.id, rule_type="price_below", threshold_value=80, enabled=True))
    db.add(
        QuickSearchPopularityCounter(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 19),
            currency="EUR",
            search_count=3,
            first_searched_at=now - dt.timedelta(days=1),
            last_searched_at=now - dt.timedelta(minutes=30),
        )
    )
    db.commit()

    snapshot = build_fare_memory_health_snapshot(db, now=now)

    top_route = snapshot["refresh_signals"]["top_routes"][0]
    assert top_route["route"] == "LEI-DUB"
    assert top_route["active_watch_count"] == 1
    assert top_route["enabled_alert_count"] == 1
    assert top_route["recent_search_count"] == 3
    assert top_route["reasons"] == [
        "active_watchlist",
        "enabled_alerts",
        "recent_searches",
        "departure_near",
    ]
    assert "health-refresh-signal@example.com" not in str(snapshot)
    assert "user_id" not in str(snapshot)
