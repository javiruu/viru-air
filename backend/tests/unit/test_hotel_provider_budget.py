import datetime as dt
import threading

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, HotelProviderBudget
from app.services.hotel_provider_budget import HotelBudgetPolicy, HotelProviderBudgetLedger


def _ledger() -> tuple[HotelProviderBudgetLedger, Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    return HotelProviderBudgetLedger(db), db


def test_zero_budget_denies_without_reservation() -> None:
    ledger, db = _ledger()
    try:
        result = ledger.reserve(
            HotelBudgetPolicy("makcorps", "revalidation", hard_limit=0),
            now=dt.datetime(2026, 8, 7, 10, 0),
        )
        assert result.allowed is False
        assert result.reason == "skipped_budget"
        row = db.scalar(select(HotelProviderBudget))
        assert row is not None
        assert row.units_reserved == 0
    finally:
        db.close()


def test_budget_reserves_up_to_limit_then_denies() -> None:
    ledger, db = _ledger()
    try:
        policy = HotelBudgetPolicy("makcorps", "revalidation", hard_limit=2)
        now = dt.datetime(2026, 8, 7, 10, 0)
        assert ledger.reserve(policy, now=now).allowed is True
        assert ledger.reserve(policy, now=now).allowed is True
        denied = ledger.reserve(policy, now=now)
        assert denied.allowed is False
        row = db.scalar(select(HotelProviderBudget))
        assert row is not None
        assert row.units_reserved == 2
    finally:
        db.close()


def test_configured_hard_limit_refreshes_for_the_current_budget_window() -> None:
    ledger, db = _ledger()
    try:
        initial = HotelBudgetPolicy("osm_overpass", "ingestion", hard_limit=2)
        assert ledger.reserve(initial, now=dt.datetime(2026, 8, 7, 10, 0)).allowed is True

        denied = ledger.reserve(
            HotelBudgetPolicy("osm_overpass", "ingestion", hard_limit=0),
            now=dt.datetime(2026, 8, 7, 10, 1),
        )

        assert denied.allowed is False
        row = db.scalar(select(HotelProviderBudget))
        assert row is not None
        assert row.hard_limit == 0
    finally:
        db.close()


def test_reservation_can_be_consumed_or_released() -> None:
    ledger, db = _ledger()
    try:
        policy = HotelBudgetPolicy("makcorps", "revalidation", hard_limit=2)
        reservation = ledger.reserve(policy, now=dt.datetime(2026, 8, 7, 10, 0))
        assert reservation.allowed is True
        assert ledger.consume(reservation, now=dt.datetime(2026, 8, 7, 10, 1)) is True
        assert ledger.consume(reservation, now=dt.datetime(2026, 8, 7, 10, 1)) is False

        row = db.scalar(select(HotelProviderBudget))
        assert row is not None
        db.expire_all()
        row = db.scalar(select(HotelProviderBudget))
        assert row is not None
        assert row.units_reserved == 0
        assert row.units_used == 1
        assert row.units_released == 0

        second = ledger.reserve(policy, now=dt.datetime(2026, 8, 7, 10, 2))
        assert second.allowed is True
        assert ledger.release(second, now=dt.datetime(2026, 8, 7, 10, 3)) is True
        assert ledger.release(second, now=dt.datetime(2026, 8, 7, 10, 3)) is False
        db.expire_all()
        row = db.scalar(select(HotelProviderBudget))
        assert row is not None
        assert row.units_reserved == 0
        assert row.units_used == 1
        assert row.units_released == 1
    finally:
        db.close()


def test_concurrent_reservations_never_exceed_limit(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'hotel-budget.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False, "timeout": 10})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    seed = factory()
    try:
        seed.add(
            HotelProviderBudget(
                provider="makcorps",
                operation="revalidation",
                window_key="2026-08-07",
                hard_limit=1,
                window_expires_at=dt.datetime(2026, 8, 8),
                updated_at=dt.datetime(2026, 8, 7, 9, 0),
            )
        )
        seed.commit()
    finally:
        seed.close()

    barrier = threading.Barrier(2)
    results: list[bool] = []
    errors: list[BaseException] = []

    def reserve_once() -> None:
        session = factory()
        try:
            barrier.wait(timeout=5)
            result = HotelProviderBudgetLedger(session).reserve(
                HotelBudgetPolicy("makcorps", "revalidation", hard_limit=1),
                now=dt.datetime(2026, 8, 7, 12, 0),
            )
            session.commit()
            results.append(result.allowed)
        except BaseException as exc:  # pragma: no cover - assertion below reports it
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=reserve_once) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    try:
        assert not errors
        assert sorted(results) == [False, True]
        check = factory()
        try:
            row = check.scalar(select(HotelProviderBudget))
            assert row is not None
            assert row.units_reserved == 1
            assert row.units_used == 0
        finally:
            check.close()
    finally:
        engine.dispose()


def test_budget_rolls_over_to_new_day() -> None:
    ledger, db = _ledger()
    try:
        policy = HotelBudgetPolicy("makcorps", "revalidation", hard_limit=1)
        assert ledger.reserve(policy, now=dt.datetime(2026, 8, 7, 23, 59)).allowed is True
        assert ledger.reserve(policy, now=dt.datetime(2026, 8, 8, 0, 1)).allowed is True
        rows = db.scalars(select(HotelProviderBudget).order_by(HotelProviderBudget.window_key)).all()
        assert len(rows) == 2
        assert [row.units_reserved for row in rows] == [1, 1]
    finally:
        db.close()
