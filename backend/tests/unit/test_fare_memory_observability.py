import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import require_admin
from app.infrastructure.db.models import (
    Base,
    FlightOfferCacheEntry,
    FlightPriceObservation,
    QuickSearchCacheEntry,
    QuickSearchNegativeCacheEntry,
    RevalidationJob,
    User,
)
from app.infrastructure.db.session import get_db
from app.main import app
from app.services.fare_memory_observability import build_fare_memory_health_snapshot


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _seed_admin_user(db: Session) -> User:
    user = User(email="admin-fare-memory@example.com", password_hash="x", is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _override_db(db: Session):
    def _get_db_override():
        yield db
    return _get_db_override


def _seed_fare_memory_records(db: Session) -> None:
    cache_entry = QuickSearchCacheEntry(
        origin_iata="LEI",
        destination_iata="DUB",
        travel_date=dt.date(2026, 7, 20),
        provider="multi",
        search_fingerprint="fsm_search_health",
        canonical_request_json='{"origin":"LEI"}',
        provider_set_json='["multi"]',
        status="ready",
        freshness_status="fresh",
        ttl_seconds=3600,
        expires_at_utc=dt.datetime(2026, 6, 16, 12, 0),
        captured_at_utc=dt.datetime(2026, 6, 16, 10, 0),
        last_accessed_at_utc=dt.datetime(2026, 6, 16, 10, 5),
        payload_json='{"results":[]}',
        warnings_json="[]",
        source_hash="qs_health_1",
        result_count=1,
        confidence_score=0.95,
    )
    expired_cache_entry = QuickSearchCacheEntry(
        origin_iata="AGP",
        destination_iata="FCO",
        travel_date=dt.date(2026, 7, 21),
        provider="multi",
        search_fingerprint="fsm_search_health_2",
        canonical_request_json='{"origin":"AGP"}',
        provider_set_json='["multi"]',
        status="degraded",
        freshness_status="warm",
        ttl_seconds=1800,
        expires_at_utc=dt.datetime(2026, 6, 15, 8, 0),
        captured_at_utc=dt.datetime(2026, 6, 15, 7, 0),
        last_accessed_at_utc=dt.datetime(2026, 6, 15, 7, 30),
        payload_json='{"results":[]}',
        warnings_json='["provider_partial_results_served"]',
        source_hash="qs_health_2",
        result_count=0,
        confidence_score=0.4,
    )
    db.add(cache_entry)
    db.add(expired_cache_entry)
    db.commit()
    db.refresh(cache_entry)

    offer = FlightOfferCacheEntry(
        offer_fingerprint="fsm_offer_health_1",
        provider="ryanair",
        carrier="FR",
        flight_number="FR12",
        origin_airport="LEI",
        destination_airport="DUB",
        departure_at=dt.datetime(2026, 7, 20, 10, 0),
        source_kind="provider",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    db.add(
        FlightPriceObservation(
            offer_id=offer.id,
            search_cache_entry_id=cache_entry.id,
            provider="ryanair",
            price_amount=99.0,
            currency="EUR",
            observed_at=dt.datetime(2026, 6, 16, 9, 0),
            expires_at=dt.datetime(2026, 6, 16, 12, 0),
            freshness_status="fresh",
            confidence_score=0.95,
            validation_status="revalidated",
            price_changed_since_last_seen=False,
        )
    )
    db.add(
        FlightPriceObservation(
            offer_id=offer.id,
            search_cache_entry_id=cache_entry.id,
            provider="ryanair",
            price_amount=119.0,
            currency="EUR",
            observed_at=dt.datetime(2026, 6, 16, 11, 0),
            expires_at=dt.datetime(2026, 6, 16, 13, 0),
            freshness_status="warm",
            confidence_score=0.4,
            validation_status="provider_partial",
            price_changed_since_last_seen=True,
            delta_abs=20.0,
            delta_pct=0.202,
        )
    )
    db.add(
        QuickSearchNegativeCacheEntry(
            negative_fingerprint="neg_health_1",
            scope="search_request",
            reason="provider_timeout",
            provider="multi",
            canonical_request_json='{"origin":"LEI","destination":"DUB"}',
            observed_at=dt.datetime(2026, 6, 16, 9, 30),
            expires_at=dt.datetime(2026, 6, 16, 12, 30),
            freshness_status="negative_fresh",
            retry_after_at=dt.datetime(2026, 6, 16, 10, 30),
            hit_count=3,
        )
    )
    db.add(
        RevalidationJob(
            job_type="boot_warmup",
            target_type="route",
            target_fingerprint="route:LEI:DUB:2026-07-20",
            provider="multi",
            priority=10,
            status="queued",
            scheduled_at=dt.datetime(2026, 6, 16, 8, 30),
        )
    )
    db.add(
        RevalidationJob(
            job_type="manual",
            target_type="route",
            target_fingerprint="route:AGP:FCO:2026-07-21",
            provider="multi",
            priority=15,
            status="failed",
            scheduled_at=dt.datetime(2026, 6, 16, 8, 0),
            finished_at=dt.datetime(2026, 6, 16, 10, 0),
            last_error_code="provider_error",
        )
    )
    db.commit()


def test_build_fare_memory_health_snapshot_returns_aggregated_safe_counts() -> None:
    db = _db()
    try:
        _seed_fare_memory_records(db)

        snapshot = build_fare_memory_health_snapshot(
            db,
            now=dt.datetime(2026, 6, 16, 10, 0),
        )

        assert snapshot["search_cache"]["total_entries"] == 2
        assert snapshot["search_cache"]["freshness"]["fresh"] == 1
        assert snapshot["search_cache"]["freshness"]["warm"] == 1
        assert snapshot["search_cache"]["expired_entries"] == 1
        assert snapshot["negative_cache"]["active_entries"] == 1
        assert snapshot["negative_cache"]["reasons"]["provider_timeout"] == 1
        assert snapshot["offer_memory"]["offer_entries"] == 1
        assert snapshot["offer_memory"]["price_observations"] == 2
        assert snapshot["offer_memory"]["changed_observations_last_24h"] == 1
        assert snapshot["revalidation_jobs"]["status"]["queued"] == 1
        assert snapshot["revalidation_jobs"]["status"]["failed"] == 1
        assert snapshot["revalidation_jobs"]["overdue_queued"] == 1
        assert snapshot["revalidation_jobs"]["failed_last_24h"] == 1
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_admin_fare_memory_health_endpoint_requires_admin_and_exposes_snapshot() -> None:
    db = _db()
    admin_user = _seed_admin_user(db)
    _seed_fare_memory_records(db)

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_admin] = lambda: admin_user
    client = TestClient(app)

    try:
        response = client.get("/api/v1/admin/fare-memory-health")

        assert response.status_code == 200
        payload = response.json()
        assert payload["search_cache"]["total_entries"] == 2
        assert payload["negative_cache"]["reasons"]["provider_timeout"] == 1
        assert payload["offer_memory"]["price_observations"] == 2
        assert payload["revalidation_jobs"]["job_type"]["boot_warmup"] == 1
        assert "canonical_request_json" not in str(payload)
    finally:
        app.dependency_overrides.clear()
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]
