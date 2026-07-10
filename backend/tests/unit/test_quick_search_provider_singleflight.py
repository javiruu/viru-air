import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, QuickSearchProviderLock
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.services.quick_search_execution import _CACHE, ExecutionPlan, ExecutionUnit, execute_plan
from app.services.quick_search_provider_singleflight import (
    acquire_quick_search_provider_lock,
    release_quick_search_provider_lock,
)


def _db_pair() -> tuple[Session, Session, Engine]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return testing_session_local(), testing_session_local(), engine


def test_provider_lock_allows_one_active_lease_per_route_day_provider() -> None:
    first_db, second_db, engine = _db_pair()
    now = dt.datetime(2026, 7, 10, 12, 0)
    try:
        first = acquire_quick_search_provider_lock(
            first_db,
            origin_iata="agp",
            destination_iata="tsf",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            currency="EUR",
            lock_ttl_seconds=30,
            now=now,
        )
        second = acquire_quick_search_provider_lock(
            second_db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            currency="EUR",
            lock_ttl_seconds=30,
            now=now + dt.timedelta(seconds=1),
        )

        rows = first_db.execute(select(QuickSearchProviderLock)).scalars().all()

        assert first is not None
        assert second is None
        assert len(rows) == 1
        assert rows[0].lock_token == first.lock_token
    finally:
        first_db.close()
        second_db.close()
        engine.dispose()


def test_provider_lock_can_be_released_and_reacquired() -> None:
    first_db, second_db, engine = _db_pair()
    now = dt.datetime(2026, 7, 10, 12, 0)
    try:
        first = acquire_quick_search_provider_lock(
            first_db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            currency="EUR",
            lock_ttl_seconds=30,
            now=now,
        )
        assert first is not None

        released = release_quick_search_provider_lock(first_db, lock_token=first.lock_token)
        second = acquire_quick_search_provider_lock(
            second_db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            currency="EUR",
            lock_ttl_seconds=30,
            now=now + dt.timedelta(seconds=2),
        )

        assert released is True
        assert second is not None
        assert second.lock_token != first.lock_token
    finally:
        first_db.close()
        second_db.close()
        engine.dispose()


def test_provider_lock_expired_lease_can_be_taken_over() -> None:
    first_db, second_db, engine = _db_pair()
    now = dt.datetime(2026, 7, 10, 12, 0)
    try:
        first = acquire_quick_search_provider_lock(
            first_db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            currency="EUR",
            lock_ttl_seconds=5,
            now=now,
        )
        second = acquire_quick_search_provider_lock(
            second_db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            currency="EUR",
            lock_ttl_seconds=5,
            now=now + dt.timedelta(seconds=6),
        )

        assert first is not None
        assert second is not None
        assert second.lock_token != first.lock_token
        assert second.expires_at == now + dt.timedelta(seconds=11)
    finally:
        first_db.close()
        second_db.close()
        engine.dispose()


def test_execute_plan_waits_for_l2_when_singleflight_lock_is_held() -> None:
    _CACHE.clear()
    calls = {"provider": 0, "shared_get": 0}
    cached_result = ProviderFetchResult(
        flights=[
            ProviderFlight(
                price=29.99,
                currency="EUR",
                departure_time_local="14:30",
                captured_at=dt.datetime(2026, 7, 10, 12, 0),
                source="singleflight-cache",
            )
        ],
        warnings=[],
    )

    def fetch_flights(origin: str, destination: str, travel_date: str, timeout_ms: int):
        calls["provider"] += 1
        return []

    def shared_cache_get(origin: str, destination: str, travel_date: dt.date | str, provider: str):
        calls["shared_get"] += 1
        return cached_result

    rows, meta, warnings = execute_plan(
        ExecutionPlan(
            units=[
                ExecutionUnit(
                    origin_iata="AGP",
                    destination_iata="TSF",
                    travel_date=dt.date(2026, 12, 25),
                    pair_priority_score=0.0,
                    pair_reason="seed-seed",
                )
            ],
            waves={"wave_1": 1, "wave_2": 0, "wave_3": 0},
            stats={},
        ),
        concurrency_limit=1,
        timeout_ms=1000,
        fetch_flights=fetch_flights,
        shared_cache_get=shared_cache_get,
        provider_singleflight_acquire=lambda origin, destination, travel_date, provider: None,
    )

    assert calls["provider"] == 0
    assert calls["shared_get"] >= 1
    assert meta["l2_cache_hits"] == 1
    assert meta["provider_calls"] == 0
    assert warnings == []
    assert rows[0][3].source == "singleflight-cache"
