import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base
from app.services.quick_search_cache_service import (
    build_effective_freshness,
    resolve_ready_cache_ttl_seconds,
    set_cache_entry,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def test_ready_ttl_ranges_follow_departure_anticipation() -> None:
    reference_now = dt.datetime(2026, 6, 15, 10, 0)

    assert resolve_ready_cache_ttl_seconds(travel_date=dt.date(2026, 9, 20), provider="multi", now=reference_now) == 12 * 60 * 60
    assert resolve_ready_cache_ttl_seconds(travel_date=dt.date(2026, 8, 20), provider="multi", now=reference_now) == 8 * 60 * 60
    assert resolve_ready_cache_ttl_seconds(travel_date=dt.date(2026, 7, 25), provider="multi", now=reference_now) == 4 * 60 * 60
    assert resolve_ready_cache_ttl_seconds(travel_date=dt.date(2026, 7, 5), provider="multi", now=reference_now) == 2 * 60 * 60
    assert resolve_ready_cache_ttl_seconds(travel_date=dt.date(2026, 6, 25), provider="multi", now=reference_now) == 45 * 60
    assert resolve_ready_cache_ttl_seconds(travel_date=dt.date(2026, 6, 17), provider="multi", now=reference_now) == 15 * 60
    assert resolve_ready_cache_ttl_seconds(travel_date=dt.date(2026, 6, 15), provider="multi", now=reference_now) == 5 * 60


def test_ready_ttl_uses_utc_normalization_for_aware_now() -> None:
    aware_now = dt.datetime(2026, 6, 15, 23, 30, tzinfo=dt.timezone(dt.timedelta(hours=2)))

    ttl = resolve_ready_cache_ttl_seconds(
        travel_date=dt.date(2026, 6, 16),
        provider="multi",
        now=aware_now,
    )

    assert ttl == 15 * 60


def test_mock_provider_ttl_is_capped_without_affecting_normal_provider() -> None:
    reference_now = dt.datetime(2026, 6, 15, 10, 0)
    travel_date = dt.date(2026, 8, 20)

    baseline = resolve_ready_cache_ttl_seconds(travel_date=travel_date, provider="multi", now=reference_now)
    mock_ttl = resolve_ready_cache_ttl_seconds(travel_date=travel_date, provider="mock", now=reference_now)

    assert baseline == 8 * 60 * 60
    assert mock_ttl == 15 * 60


def test_past_departure_never_serializes_as_fresh() -> None:
    db = _db()
    try:
        entry = set_cache_entry(
            db,
            origin_iata="LEI",
            destination_iata="FCO",
            travel_date=dt.date(2026, 6, 14),
            provider="multi",
            source_hash="qs_past_departure",
            category="ready",
            payload_json='{"flights":[]}',
            warnings_json="[]",
        )

        freshness = build_effective_freshness(
            entry,
            now=dt.datetime(2026, 6, 15, 10, 0),
        )

        assert freshness["status"] == "expired"
        assert freshness["requires_revalidation"] is True
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
