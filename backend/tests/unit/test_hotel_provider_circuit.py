from __future__ import annotations

import datetime as dt

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.models import Base, HotelProviderCircuit, HotelProviderRun
from app.services.hotel_provider_circuit import HotelProviderCircuitStore


def _db(url: str = "sqlite:///:memory:"):
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_circuit_opens_after_threshold_and_blocks_admission() -> None:
    engine, db = _db()
    try:
        store = HotelProviderCircuitStore(db)
        now = dt.datetime(2026, 8, 7, 12)
        first = store.admit("makcorps", "area_search", now=now, failure_threshold=2, cooldown_seconds=30)
        assert first.allowed and first.permit is not None
        assert store.record(first.permit, "timeout", now=now) is True

        second = store.admit("makcorps", "area_search", now=now)
        assert second.allowed and second.permit is not None
        assert store.record(second.permit, "provider_5xx", now=now) is True

        blocked = store.admit("makcorps", "area_search", now=now + dt.timedelta(seconds=1))
        assert blocked.allowed is False
        assert blocked.reason == "skipped_circuit"
        row = db.scalar(select(HotelProviderCircuit))
        assert row is not None
        assert row.status == "open"
        assert row.consecutive_failures == 2
        assert row.state_version == 2
    finally:
        db.close()
        engine.dispose()


def test_expired_open_circuit_allows_one_half_open_probe() -> None:
    engine, db = _db()
    try:
        store = HotelProviderCircuitStore(db)
        now = dt.datetime(2026, 8, 7, 12)
        permit = store.admit("makcorps", "revalidation", now=now, failure_threshold=1, cooldown_seconds=30)
        assert permit.permit is not None
        store.record(permit.permit, "timeout", now=now)

        probe = store.admit("makcorps", "revalidation", now=now + dt.timedelta(seconds=31))
        assert probe.allowed is True
        assert probe.reason == "half_open_probe"
        assert probe.permit is not None and probe.permit.probe_token is not None

        second_probe = store.admit("makcorps", "revalidation", now=now + dt.timedelta(seconds=31))
        assert second_probe.allowed is False
        assert store.record(probe.permit, "success", now=now + dt.timedelta(seconds=32)) is True

        recovered = store.admit("makcorps", "revalidation", now=now + dt.timedelta(seconds=33))
        assert recovered.allowed is True
        row = db.scalar(select(HotelProviderCircuit))
        assert row is not None
        assert row.status == "closed"
        assert row.consecutive_failures == 0
    finally:
        db.close()
        engine.dispose()


def test_expired_half_open_probe_can_be_reclaimed() -> None:
    engine, db = _db()
    try:
        store = HotelProviderCircuitStore(db)
        now = dt.datetime(2026, 8, 7, 12)
        first = store.admit(
            "makcorps",
            "area_search",
            now=now,
            failure_threshold=1,
            cooldown_seconds=30,
            probe_ttl_seconds=5,
        )
        assert first.permit is not None
        assert store.record(first.permit, "timeout", now=now)

        probe = store.admit("makcorps", "area_search", now=now + dt.timedelta(seconds=31), probe_ttl_seconds=5)
        assert probe.permit is not None and probe.permit.probe_token is not None
        reclaimed = store.admit("makcorps", "area_search", now=now + dt.timedelta(seconds=37), probe_ttl_seconds=5)
        assert reclaimed.allowed is True
        assert reclaimed.reason == "half_open_probe"
        assert reclaimed.permit is not None
        assert reclaimed.permit.probe_token != probe.permit.probe_token
        assert store.record(probe.permit, "success", now=now + dt.timedelta(seconds=38)) is False
        assert store.record(reclaimed.permit, "success", now=now + dt.timedelta(seconds=38)) is True
    finally:
        db.close()
        engine.dispose()


def test_multiple_closed_permits_accumulate_failures() -> None:
    engine, db = _db()
    try:
        store = HotelProviderCircuitStore(db)
        now = dt.datetime(2026, 8, 7, 12)
        first = store.admit("makcorps", "area_search", now=now, failure_threshold=3)
        second = store.admit("makcorps", "area_search", now=now)
        assert first.permit is not None and second.permit is not None
        assert first.permit.state_version == 0
        assert second.permit.state_version == 0
        assert store.record(second.permit, "timeout", now=now) is True
        assert store.record(first.permit, "timeout", now=now) is True
        row = db.scalar(select(HotelProviderCircuit))
        assert row is not None
        assert row.consecutive_failures == 2
        assert row.state_version == 2
    finally:
        db.close()
        engine.dispose()


def test_circuit_transaction_does_not_commit_callers_pending_work(tmp_path) -> None:
    db_path = tmp_path / "circuit-isolation.db"
    engine, db = _db(f"sqlite:///{db_path}")
    try:
        pending_run_id = "pending-uncommitted-run"
        pending_run = HotelProviderRun(id=pending_run_id, provider="makcorps", status="running")
        db.add(pending_run)
        store = HotelProviderCircuitStore(db)
        admission = store.admit("makcorps", "area_search", now=dt.datetime(2026, 8, 7, 12))
        assert admission.allowed

        db.close()
        with sessionmaker(bind=engine)() as fresh_db:
            assert fresh_db.get(HotelProviderRun, pending_run_id) is None
            assert fresh_db.scalar(
                select(HotelProviderCircuit).where(
                    HotelProviderCircuit.provider == "makcorps",
                    HotelProviderCircuit.operation == "area_search",
                )
            ) is not None
    finally:
        engine.dispose()


def test_empty_is_a_successful_probe_and_does_not_open_circuit() -> None:
    engine, db = _db()
    try:
        store = HotelProviderCircuitStore(db)
        now = dt.datetime(2026, 8, 7, 12)
        permit = store.admit("makcorps", "area_search", now=now, failure_threshold=1)
        assert permit.permit is not None
        assert store.record(permit.permit, "empty", now=now) is True
        row = db.scalar(select(HotelProviderCircuit))
        assert row is not None
        assert row.status == "closed"
        assert row.consecutive_failures == 0
    finally:
        db.close()
        engine.dispose()
