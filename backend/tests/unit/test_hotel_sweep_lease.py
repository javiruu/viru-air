from __future__ import annotations

import datetime as dt
import threading

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.models import Base, HotelSweepLease
from app.services.hotel_sweep_lease import HotelSweepLeaseStore, stay_query_fingerprint


def _factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'hotel-lease.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)


def _fingerprint(**overrides) -> str:
    values = {
        "provider": "makcorps",
        "operation": "revalidation",
        "canonical_hotel_id": "hotel-1",
        "provider_hotel_id": "external-1",
        "check_in": "2026-09-01",
        "check_out": "2026-09-03",
        "guests": 2,
        "currency": "EUR",
    }
    values.update(overrides)
    return stay_query_fingerprint(**values)


def test_fingerprint_is_stable_and_covers_price_dimensions() -> None:
    assert _fingerprint() == _fingerprint()
    assert _fingerprint(currency="USD") != _fingerprint(currency="EUR")
    assert _fingerprint(guests=3) != _fingerprint(guests=2)
    assert _fingerprint(room_label="suite") != _fingerprint(room_label="double")
    assert _fingerprint(rooms=2) != _fingerprint(rooms=1)
    assert _fingerprint(children_ages=(4,)) != _fingerprint(children_ages=())
    assert _fingerprint(room_id="room-a") != _fingerprint(room_id="room-b")


def test_only_one_worker_claims_active_fingerprint(tmp_path) -> None:
    engine, factory = _factory(tmp_path)
    fingerprint = _fingerprint()
    barrier = threading.Barrier(2)
    outcomes: list[bool] = []
    errors: list[BaseException] = []
    now = dt.datetime(2026, 8, 7, 12, 0)

    def claim() -> None:
        db = factory()
        try:
            barrier.wait(timeout=5)
            outcomes.append(HotelSweepLeaseStore(db).acquire(fingerprint, now=now, ttl_seconds=30) is not None)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    try:
        assert not errors
        assert sorted(outcomes) == [False, True]
        db = factory()
        try:
            row = db.scalar(select(HotelSweepLease).where(HotelSweepLease.fingerprint == fingerprint))
            assert row is not None
            assert row.attempt_count == 1
            assert row.status == "running"
        finally:
            db.close()
    finally:
        engine.dispose()


def test_expired_lease_can_be_taken_over_but_old_token_cannot_finish(tmp_path) -> None:
    engine, factory = _factory(tmp_path)
    db = factory()
    try:
        store = HotelSweepLeaseStore(db)
        first = store.acquire(_fingerprint(), now=dt.datetime(2026, 8, 7, 12, 0), ttl_seconds=10)
        assert first is not None
        second = store.acquire(_fingerprint(), now=dt.datetime(2026, 8, 7, 12, 11), ttl_seconds=10)
        assert second is not None
        assert second.lock_token != first.lock_token
        assert store.finish(first, status="done", now=dt.datetime(2026, 8, 7, 12, 12)) is False
        assert store.owns_active_lease(second, now=dt.datetime(2026, 8, 7, 12, 11, 5)) is True
        assert store.finish(second, status="done", now=dt.datetime(2026, 8, 7, 12, 11, 5), provider_run_id="run-1") is True
    finally:
        db.close()
        engine.dispose()


def test_renew_requires_current_unexpired_owner(tmp_path) -> None:
    engine, factory = _factory(tmp_path)
    db = factory()
    try:
        store = HotelSweepLeaseStore(db)
        lease = store.acquire(_fingerprint(), now=dt.datetime(2026, 8, 7, 12, 0), ttl_seconds=10)
        assert lease is not None
        assert store.renew(lease, now=dt.datetime(2026, 8, 7, 12, 0, 5), ttl_seconds=10) is True
        assert store.renew(lease, now=dt.datetime(2026, 8, 7, 12, 0, 20), ttl_seconds=10) is False
    finally:
        db.close()
        engine.dispose()
