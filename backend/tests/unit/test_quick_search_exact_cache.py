import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base
from app.services.quick_search_cache_service import (
    build_effective_freshness,
    deserialize_exact_search_payload,
    get_exact_search_cache_entry,
    set_exact_search_cache_entry,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return TestingSessionLocal()


def test_exact_search_cache_roundtrip_persists_response_payload() -> None:
    db = _db()
    try:
        payload = {
            "meta": {"query_signature": "qsig_123"},
            "results": [{"result_id": "LEI-DUB-2026-06-14-0", "price_total": 55}],
        }
        entry = set_exact_search_cache_entry(
            db,
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 14),
            search_fingerprint="fsm_search_123",
            canonical_request_json='{"origin":{"seed_iata":"LEI"}}',
            provider_set_json='["multi"]',
            response_payload=payload,
            category="ready",
            confidence_score=0.95,
        )

        fetched = get_exact_search_cache_entry(
            db,
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 14),
            search_fingerprint="fsm_search_123",
        )

        assert fetched is not None
        assert fetched.id == entry.id
        assert fetched.provider == "search_exact"
        assert fetched.search_fingerprint == "fsm_search_123"
        assert fetched.result_count == 1
        assert deserialize_exact_search_payload(fetched.payload_json)["results"][0]["price_total"] == 55
    finally:
        db.close()


def test_exact_search_cache_freshness_can_degrade_to_warm() -> None:
    db = _db()
    try:
        entry = set_exact_search_cache_entry(
            db,
            origin_iata="LEI",
            destination_iata="DUB",
            travel_date=dt.date(2026, 6, 14),
            search_fingerprint="fsm_search_456",
            canonical_request_json="{}",
            provider_set_json='["multi"]',
            response_payload={"meta": {}, "results": [{"result_id": "x"}]},
            category="ready",
        )
        entry.captured_at_utc = entry.captured_at_utc - dt.timedelta(seconds=max(1, entry.ttl_seconds // 2 + 60))
        db.add(entry)
        db.commit()
        db.refresh(entry)

        freshness = build_effective_freshness(entry)

        assert freshness["status"] == "warm"
        assert freshness["requires_revalidation"] is True
    finally:
        db.close()
