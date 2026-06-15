import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base
from app.services.quick_search_cache_service import (
    build_negative_cache_fingerprint,
    get_fresh_negative_cache_entry,
    resolve_negative_cache_result,
    set_negative_cache_entry,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return TestingSessionLocal()


def test_negative_cache_entry_roundtrip_for_no_availability() -> None:
    db = _db()
    try:
        fingerprint = build_negative_cache_fingerprint(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 15),
            provider="multi",
        )
        set_negative_cache_entry(
            db,
            negative_fingerprint=fingerprint,
            scope="route_date_provider",
            reason="no_availability",
            provider="multi",
            canonical_request_json='{"origin":"LEI","destination":"DUB"}',
        )

        entry = get_fresh_negative_cache_entry(db, negative_fingerprint=fingerprint)

        assert entry is not None
        assert entry.reason == "no_availability"
        assert entry.hit_count == 1
        result = resolve_negative_cache_result(entry)
        assert result.flights == []
        assert result.warnings == []
    finally:
        db.close()


def test_negative_cache_entry_roundtrip_for_provider_timeout() -> None:
    db = _db()
    try:
        fingerprint = build_negative_cache_fingerprint(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 15),
            provider="multi",
        )
        retry_after = dt.datetime(2026, 6, 15, 10, 10)
        set_negative_cache_entry(
            db,
            negative_fingerprint=fingerprint,
            scope="route_date_provider",
            reason="provider_timeout",
            provider="multi",
            canonical_request_json='{"origin":"LEI","destination":"DUB"}',
            retry_after_at=retry_after,
        )

        entry = get_fresh_negative_cache_entry(db, negative_fingerprint=fingerprint)

        assert entry is not None
        assert entry.reason == "provider_timeout"
        assert entry.retry_after_at == retry_after
        result = resolve_negative_cache_result(entry)
        assert result.flights == []
        assert result.warnings == ["provider_timeout_partial"]
    finally:
        db.close()


def test_expired_negative_cache_entry_returns_none() -> None:
    db = _db()
    try:
        fingerprint = build_negative_cache_fingerprint(
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 15),
            provider="multi",
        )
        entry = set_negative_cache_entry(
            db,
            negative_fingerprint=fingerprint,
            scope="route_date_provider",
            reason="no_availability",
            provider="multi",
            canonical_request_json="{}",
        )
        entry.expires_at = dt.datetime(2026, 6, 15, 9, 0)
        db.add(entry)
        db.commit()

        assert get_fresh_negative_cache_entry(db, negative_fingerprint=fingerprint) is None
    finally:
        db.close()
