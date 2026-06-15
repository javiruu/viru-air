import datetime as dt
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import ProviderFetchResult
from app.infrastructure.db.models import AlertRule, Base, FlightWatch, NotificationEvent, PriceSnapshot, User
from app.services.alert_service import evaluate_rules_for_watch


class _ProviderStub:
    def __init__(self, *, flights=None, error: Exception | None = None):
        self._flights = flights or []
        self._error = error

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000, currency: str = "EUR"):
        if self._error is not None:
            raise self._error
        return ProviderFetchResult(flights=list(self._flights), warnings=[])


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _flight(*, price: float, departure_time_local: str = "10:00", currency: str = "EUR", source: str = "stub-provider"):
    return type(
        "ProviderFlightStub",
        (),
        {
            "price": price,
            "currency": currency,
            "departure_time_local": departure_time_local,
            "source": source,
        },
    )()


def _seed_watch_with_rule(db: Session, *, threshold_value: float = 50.0) -> tuple[User, FlightWatch, AlertRule]:
    user = User(email="alert-test@example.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    watch = FlightWatch(
        user_id=user.id,
        origin_iata="LEI",
        destination_iata="FCO",
        travel_date_local=dt.date(2026, 7, 20),
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)

    rule = AlertRule(
        watch_id=watch.id,
        rule_type="threshold_low",
        threshold_value=threshold_value,
        cooldown_minutes=60,
        enabled=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return user, watch, rule


def _seed_snapshot(
    db: Session,
    *,
    watch_id: str,
    price: float,
    captured_at: dt.datetime,
    is_stale: bool,
) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        watch_id=watch_id,
        captured_at_utc=captured_at,
        departure_time_local="10:00",
        raw_price=price,
        raw_currency="EUR",
        provider="seed-provider",
        is_stale=is_stale,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def test_alert_does_not_trigger_with_stale_snapshot_without_revalidation() -> None:
    db = _db()
    try:
        _, watch, _ = _seed_watch_with_rule(db, threshold_value=50.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            price=45.0,
            captured_at=dt.datetime(2026, 7, 20, 8, 0),
            is_stale=True,
        )

        events = evaluate_rules_for_watch(db, watch.id, attempt_revalidation=False)

        assert events == []
        assert db.execute(select(NotificationEvent)).scalars().all() == []
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_revalidation_confirming_drop_triggers_alert() -> None:
    db = _db()
    try:
        _, watch, rule = _seed_watch_with_rule(db, threshold_value=50.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            price=60.0,
            captured_at=dt.datetime(2026, 7, 20, 7, 0),
            is_stale=False,
        )
        _seed_snapshot(
            db,
            watch_id=watch.id,
            price=55.0,
            captured_at=dt.datetime(2026, 7, 20, 8, 0),
            is_stale=True,
        )

        events = evaluate_rules_for_watch(
            db,
            watch.id,
            provider_client=_ProviderStub(flights=[_flight(price=45.0)]),
        )

        snapshots = (
            db.execute(select(PriceSnapshot).where(PriceSnapshot.watch_id == watch.id).order_by(PriceSnapshot.captured_at_utc.asc()))
            .scalars()
            .all()
        )
        revalidated = [snapshot for snapshot in snapshots if snapshot.is_stale is False and float(snapshot.raw_price) == 45.0]
        assert len(events) == 1
        assert events[0].rule_id == rule.id
        assert "Precio bajo: 45.00 EUR" in events[0].message
        assert len(snapshots) == 3
        assert len(revalidated) >= 1
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_revalidation_higher_price_records_snapshot_without_triggering_alert() -> None:
    db = _db()
    try:
        _, watch, _ = _seed_watch_with_rule(db, threshold_value=50.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            price=45.0,
            captured_at=dt.datetime(2026, 7, 20, 8, 0),
            is_stale=True,
        )

        events = evaluate_rules_for_watch(
            db,
            watch.id,
            provider_client=_ProviderStub(flights=[_flight(price=65.0)]),
        )

        snapshots = (
            db.execute(select(PriceSnapshot).where(PriceSnapshot.watch_id == watch.id).order_by(PriceSnapshot.captured_at_utc.asc()))
            .scalars()
            .all()
        )
        revalidated = [snapshot for snapshot in snapshots if snapshot.is_stale is False and float(snapshot.raw_price) == 65.0]
        assert events == []
        assert len(snapshots) == 2
        assert len(revalidated) == 1
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_provider_failure_creates_honest_revalidation_event() -> None:
    db = _db()
    try:
        _, watch, rule = _seed_watch_with_rule(db, threshold_value=50.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            price=45.0,
            captured_at=dt.datetime(2026, 7, 20, 8, 0),
            is_stale=True,
        )

        events = evaluate_rules_for_watch(
            db,
            watch.id,
            provider_client=_ProviderStub(error=RuntimeError("provider unavailable")),
        )

        assert len(events) == 1
        assert events[0].rule_id == rule.id
        assert events[0].group_reason == "revalidation_failed"
        assert "no pudimos revalidar" in events[0].message.lower()
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_revalidation_success_logs_metrics(caplog) -> None:
    db = _db()
    try:
        _, watch, _ = _seed_watch_with_rule(db, threshold_value=50.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            price=55.0,
            captured_at=dt.datetime(2026, 7, 20, 8, 0),
            is_stale=True,
        )

        with caplog.at_level(logging.INFO, logger="app.services.alert_service"):
            evaluate_rules_for_watch(
                db,
                watch.id,
                provider_client=_ProviderStub(flights=[_flight(price=45.0)]),
            )

        assert "revalidation_success_count=1" in caplog.text
        assert "revalidation_price_changed_count=1" in caplog.text
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_revalidation_failure_logs_provider_error_metrics(caplog) -> None:
    db = _db()
    try:
        _, watch, _ = _seed_watch_with_rule(db, threshold_value=50.0)
        _seed_snapshot(
            db,
            watch_id=watch.id,
            price=45.0,
            captured_at=dt.datetime(2026, 7, 20, 8, 0),
            is_stale=True,
        )

        with caplog.at_level(logging.WARNING, logger="app.services.alert_service"):
            evaluate_rules_for_watch(
                db,
                watch.id,
                provider_client=_ProviderStub(error=RuntimeError("provider unavailable")),
            )

        assert "revalidation_success_count=0" in caplog.text
        assert "provider_error_count=1" in caplog.text
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
