import datetime as dt
import json
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base
from app.services.quick_search_cache_service import (
    get_fresh_entry,
    get_fresh_negative_cache_entry,
    resolve_negative_cache_result,
    set_cache_entry,
    set_negative_cache_entry,
)
from app.services.quick_search_redis_hot_layer import (
    read_positive_cache_entry_from_redis,
    write_positive_cache_entry_to_redis,
)


@dataclass(slots=True)
class FakeRedis:
    values: dict[str, str]
    ttl_by_key: dict[str, int]

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def setex(self, name: str, time: int, value: str) -> bool:
        self.values[name] = value
        self.ttl_by_key[name] = time
        return True


class FailingRedis:
    def get(self, name: str) -> str | None:
        raise ConnectionError("redis down")

    def setex(self, name: str, time: int, value: str) -> bool:
        raise ConnectionError("redis down")


def _db() -> tuple[Session, Engine]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return testing_session_local(), engine


def test_positive_redis_hit_returns_cache_entry_without_db_lookup() -> None:
    redis = FakeRedis(values={}, ttl_by_key={})
    now = dt.datetime(2026, 7, 10, 12, 0)
    db, engine = _db()
    try:
        entry = set_cache_entry(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            source_hash="qs_redis_hit",
            category="ready",
            payload_json=json.dumps({"flights": [{"price": 29.99, "currency": "EUR"}]}),
            warnings_json="[]",
        )
        write_positive_cache_entry_to_redis(entry, now=now, redis_client=redis)
    finally:
        db.close()
        engine.dispose()

    empty_db, empty_engine = _db()
    try:
        cached = get_fresh_entry(
            empty_db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            source_hash="qs_redis_hit",
            redis_client=redis,
        )
    finally:
        empty_db.close()
        empty_engine.dispose()

    direct_cached = read_positive_cache_entry_from_redis(
        origin_iata="AGP",
        destination_iata="TSF",
        travel_date=dt.date(2026, 12, 25),
        provider="multi",
        source_hash="qs_redis_hit",
        now=now,
        redis_client=redis,
    )

    assert cached is not None
    assert cached.payload_json == json.dumps({"flights": [{"price": 29.99, "currency": "EUR"}]})
    assert cached.source_hash == "qs_redis_hit"
    assert direct_cached is not None
    assert direct_cached.source_hash == "qs_redis_hit"


def test_redis_write_failure_does_not_break_db_cache_persist() -> None:
    db, engine = _db()
    try:
        entry = set_cache_entry(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            source_hash="qs_redis_down",
            category="ready",
            payload_json='{"flights":[]}',
            warnings_json="[]",
            redis_client=FailingRedis(),
        )

        cached = get_fresh_entry(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            source_hash="qs_redis_down",
            redis_client=FailingRedis(),
        )

        assert entry.source_hash == "qs_redis_down"
        assert cached is not None
        assert cached.source_hash == "qs_redis_down"
    finally:
        db.close()
        engine.dispose()


def test_positive_redis_ttl_does_not_exceed_db_remaining_ttl() -> None:
    redis = FakeRedis(values={}, ttl_by_key={})
    now = dt.datetime(2026, 7, 10, 12, 0)
    db, engine = _db()
    try:
        entry = set_cache_entry(
            db,
            origin_iata="AGP",
            destination_iata="TSF",
            travel_date=dt.date(2026, 12, 25),
            provider="multi",
            source_hash="qs_redis_ttl",
            category="ready",
            payload_json='{"flights":[]}',
            warnings_json="[]",
        )
        entry.expires_at_utc = now + dt.timedelta(seconds=42)

        write_positive_cache_entry_to_redis(entry, now=now, redis_client=redis, max_ttl_seconds=300)

        assert redis.ttl_by_key["qs:result:qs_redis_ttl"] == 42
    finally:
        db.close()
        engine.dispose()


def test_negative_redis_hit_returns_explicit_provider_warning() -> None:
    redis = FakeRedis(values={}, ttl_by_key={})
    db, engine = _db()
    try:
        entry = set_negative_cache_entry(
            db,
            negative_fingerprint="qsn_redis_negative",
            scope="route_date_provider",
            reason="provider_timeout",
            provider="multi",
            canonical_request_json='{"origin":"AGP","destination":"TSF"}',
            redis_client=redis,
        )
    finally:
        db.close()
        engine.dispose()

    empty_db, empty_engine = _db()
    try:
        cached = get_fresh_negative_cache_entry(
            empty_db,
            negative_fingerprint=entry.negative_fingerprint,
            redis_client=redis,
        )
    finally:
        empty_db.close()
        empty_engine.dispose()

    assert cached is not None
    assert resolve_negative_cache_result(cached).warnings == ["provider_timeout_partial"]
