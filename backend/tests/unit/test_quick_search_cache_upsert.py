import datetime as dt
import json

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, QuickSearchCacheEntry
from app.services.quick_search_cache_service import set_cache_entry
from app.services.quick_search_cache_upsert import (
    QuickSearchCacheUpsertValues,
    _build_postgresql_upsert,
)


def _db() -> tuple[Session, Engine]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return testing_session_local(), engine


def test_set_cache_entry_updates_existing_row_for_same_unit_key() -> None:
    db, engine = _db()
    travel_date = dt.date(2026, 12, 25)
    source_hash = "same-source-hash"
    try:
        first_entry = set_cache_entry(
            db,
            origin_iata=" agp ",
            destination_iata="tsf",
            travel_date=travel_date,
            provider=" MULTI ",
            source_hash=source_hash,
            category="ready",
            payload_json=json.dumps({"marker": "first", "flights": []}),
            warnings_json="[]",
            provider_latency_ms=111,
        )

        second_entry = set_cache_entry(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=travel_date,
            provider="multi",
            source_hash=source_hash,
            category="degraded",
            payload_json=json.dumps({"marker": "second", "flights": []}),
            warnings_json=json.dumps(["provider_timeout_partial"]),
            provider_latency_ms=222,
        )

        row_count = db.scalar(select(func.count(QuickSearchCacheEntry.id)))
        persisted = db.scalar(select(QuickSearchCacheEntry))

        assert row_count == 1
        assert persisted is not None
        assert second_entry.id == first_entry.id == persisted.id
        assert json.loads(persisted.payload_json)["marker"] == "second"
        assert json.loads(persisted.warnings_json) == ["provider_timeout_partial"]
        assert persisted.status == "degraded"
        assert persisted.provider_latency_ms == 222
        assert persisted.search_fingerprint is None
        assert persisted.result_count == 0
    finally:
        db.close()
        engine.dispose()


def test_postgresql_upsert_targets_cache_unique_constraint() -> None:
    now = dt.datetime(2026, 7, 10, 12, 0)
    stmt = _build_postgresql_upsert(
        QuickSearchCacheUpsertValues(
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            source_hash="same-source-hash",
            status="ready",
            ttl_seconds=3600,
            expires_at_utc=now + dt.timedelta(hours=1),
            captured_at_utc=now,
            last_accessed_at_utc=now,
            payload_json='{"flights":[]}',
            warnings_json="[]",
        )
    )

    compiled = str(stmt.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT ON CONSTRAINT uq_quick_search_cache_unit DO UPDATE" in compiled
    assert "payload_json = excluded.payload_json" in compiled
