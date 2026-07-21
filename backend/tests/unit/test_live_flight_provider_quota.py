import datetime as dt
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, select

from app.infrastructure.db.models import FlightProviderQuota
from app.infrastructure.db.session import Base
from app.services.live_flight_provider_quota import (
    ProviderBudgetPolicy,
    SqlAlchemyProviderQuotaLedger,
)


def _ledger():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SqlAlchemyProviderQuotaLedger(engine), engine


def test_quota_reservation_stops_before_hard_limit_and_resets_next_month() -> None:
    ledger, engine = _ledger()
    policy = ProviderBudgetPolicy("aviationstack", "month", hard_limit=2, units_per_request=1)
    july = dt.datetime(2026, 7, 31, 23, 59)

    assert ledger.reserve(policy, july) is True
    assert ledger.reserve(policy, july) is True
    assert ledger.reserve(policy, july) is False
    assert ledger.reserve(policy, dt.datetime(2026, 8, 1)) is True

    with engine.connect() as connection:
        row = connection.execute(select(FlightProviderQuota)).one()
    assert row.window_key == "2026-08"
    assert row.units_used == 1


def test_provider_block_is_persistent_and_expires() -> None:
    ledger, _ = _ledger()
    policy = ProviderBudgetPolicy("opensky", "day", hard_limit=8, units_per_request=4)
    now = dt.datetime(2026, 7, 22, 8, 30)

    ledger.block("opensky", now, seconds=120, reason="rate_limited")

    assert ledger.reserve(policy, now + dt.timedelta(seconds=119)) is False
    assert ledger.reserve(policy, now + dt.timedelta(seconds=121)) is True


def test_concurrent_reservations_cannot_exceed_hard_limit(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'quota-concurrency.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    ledger = SqlAlchemyProviderQuotaLedger(engine)
    policy = ProviderBudgetPolicy("aviationstack", "month", hard_limit=3, units_per_request=1)
    now = dt.datetime(2026, 7, 22, 8, 30)

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: ledger.reserve(policy, now), range(10)))

    assert sum(results) == 3
    with engine.connect() as connection:
        row = connection.execute(select(FlightProviderQuota)).one()
    assert row.units_used == 3
