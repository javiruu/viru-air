import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, QuickSearchProviderLock
from app.services.quick_search_provider_singleflight import (
    acquire_quick_search_provider_lock,
    release_quick_search_provider_lock,
)


@dataclass(slots=True)
class FakeRedisLock:
    values: dict[str, str] = field(default_factory=dict)

    def set(self, name: str, value: str, nx: bool, ex: int) -> bool | None:
        if nx and name in self.values:
            return None
        self.values[name] = value
        return True

    def eval(self, script: str, numkeys: int, *args: str) -> int:
        key, token = args
        if self.values.get(key) != token:
            return 0
        del self.values[key]
        return 1


class FailingRedisLock:
    def set(self, name: str, value: str, nx: bool, ex: int) -> bool | None:
        raise ConnectionError("redis down")

    def eval(self, script: str, numkeys: int, *args: str) -> int:
        raise ConnectionError("redis down")


def _db() -> tuple[Session, Engine]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return testing_session_local(), engine


def test_redis_lock_blocks_duplicate_provider_lease_without_db_row() -> None:
    redis = FakeRedisLock()
    db, engine = _db()
    try:
        first = acquire_quick_search_provider_lock(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            redis_client=redis,
        )
        second = acquire_quick_search_provider_lock(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            redis_client=redis,
        )

        db_lock_count = db.scalar(select(func.count(QuickSearchProviderLock.lock_key)))

        assert first is not None
        assert second is None
        assert first.lock_token.startswith("redis:")
        assert db_lock_count == 0
    finally:
        db.close()
        engine.dispose()


def test_redis_lock_release_allows_reacquire() -> None:
    redis = FakeRedisLock()
    db, engine = _db()
    try:
        first = acquire_quick_search_provider_lock(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            redis_client=redis,
        )
        assert first is not None

        released = release_quick_search_provider_lock(db, lock_token=first.lock_token, redis_client=redis)
        second = acquire_quick_search_provider_lock(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            redis_client=redis,
        )

        assert released is True
        assert second is not None
        assert second.lock_token != first.lock_token
    finally:
        db.close()
        engine.dispose()


def test_redis_lock_down_does_not_fallback_to_db_lock() -> None:
    db, engine = _db()
    try:
        lease = acquire_quick_search_provider_lock(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            redis_client=FailingRedisLock(),
        )
        db_lock_count = db.scalar(select(func.count(QuickSearchProviderLock.lock_key)))

        assert lease is None
        assert db_lock_count == 0
    finally:
        db.close()
        engine.dispose()
