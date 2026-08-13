from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelProviderAlias,
    HotelProviderLatencyAggregate,
    HotelProperty,
    User,
)
from app.services.hotels_service import create_tracked_offer
import app.services.hotels_service as hotels_service


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _close(db: Session) -> None:
    engine = db._test_engine  # type: ignore[attr-defined]
    db.close()
    engine.dispose()


def _enable(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")


@pytest.mark.parametrize("profile", ["rate_limited_429", "provider_timeout", "invalid_json"])
def test_run_hotel_sweep_selects_env_fault_profile_and_persists_latency(monkeypatch, profile) -> None:
    _enable(monkeypatch)
    monkeypatch.setenv("HOTEL_MOCK_FAULT_PROFILE", profile)

    db = _db()
    try:
        result = hotels_service.run_hotel_sweep(db, provider="mock")
        assert result.status == "failed"
        assert result.error_message
        aggregate = db.scalar(
            select(HotelProviderLatencyAggregate).where(
                HotelProviderLatencyAggregate.provider_run_id == result.id,
                HotelProviderLatencyAggregate.operation == "ingestion",
            )
        )
        assert aggregate is not None
        assert aggregate.outcome in {"rate_limited", "timeout", "invalid_response"}
        assert aggregate.error_code in {"rate_limited", "timeout", "invalid_response"}
        assert aggregate.sample_count == 1
        assert result.tracked_outcomes is not None
    finally:
        _close(db)


@pytest.mark.parametrize("profile", ["rate_limited_429", "provider_timeout", "invalid_json"])
def test_run_hotel_sweep_persists_revalidation_latency_for_env_fault_profile(monkeypatch, profile) -> None:
    _enable(monkeypatch)
    monkeypatch.setenv("HOTEL_MOCK_FAULT_PROFILE", profile)

    db = _db()
    try:
        user = User(email=f"h44-revalidation-{profile}@example.test", password_hash="hash")
        hotel = HotelProperty(
            canonical_name="Hotel Sol Madrid",
            normalized_name="hotel sol madrid",
            city="Madrid",
            normalized_city="madrid",
            country_code="ES",
            latitude=40.4169,
            longitude=-3.7036,
            stars=4,
        )
        db.add_all([user, hotel])
        db.flush()
        create_tracked_offer(
            db,
            user_id=user.id,
            hotel_id=hotel.id,
            check_in=date(2026, 7, 10),
            check_out=date(2026, 7, 12),
            guests=2,
            provider="mock",
            initial_price=250.00,
            currency="EUR",
        )
        db.add(HotelProviderAlias(
            hotel_id=hotel.id,
            provider="mock",
            provider_hotel_id="mock-sol-001",
        ))
        db.commit()
        monkeypatch.setattr(
            hotels_service.HotelIngestionService,
            "ingest",
            lambda self: SimpleNamespace(hotels_processed=0),
        )

        result = hotels_service.run_hotel_sweep(db, provider="mock")

        assert result.status == "failed"
        aggregate = db.scalar(
            select(HotelProviderLatencyAggregate).where(
                HotelProviderLatencyAggregate.provider_run_id == result.id,
                HotelProviderLatencyAggregate.operation == "revalidation",
            )
        )
        assert aggregate is not None
        expected = {
            "rate_limited_429": ("rate_limited", "rate_limited"),
            "provider_timeout": ("timeout", "timeout"),
            "invalid_json": ("invalid_response", "invalid_response"),
        }[profile]
        assert (aggregate.outcome, aggregate.error_code) == expected
        assert aggregate.sample_count == 1
    finally:
        _close(db)


def test_run_hotel_sweep_uses_env_sold_out_profile_for_revalidation(monkeypatch) -> None:
    _enable(monkeypatch)
    monkeypatch.setenv("HOTEL_MOCK_FAULT_PROFILE", "sold_out")

    db = _db()
    try:
        user = User(email="h44-worker@example.test", password_hash="hash")
        hotel = HotelProperty(
            canonical_name="Hotel Sol Madrid",
            normalized_name="hotel sol madrid",
            city="Madrid",
            normalized_city="madrid",
            country_code="ES",
            latitude=40.4169,
            longitude=-3.7036,
            stars=4,
        )
        db.add_all([user, hotel])
        db.flush()
        offer = create_tracked_offer(
            db,
            user_id=user.id,
            hotel_id=hotel.id,
            check_in=date(2026, 7, 10),
            check_out=date(2026, 7, 12),
            guests=2,
            provider="mock",
            initial_price=250.00,
            currency="EUR",
        )
        db.add(HotelProviderAlias(
            hotel_id=hotel.id,
            provider="mock",
            provider_hotel_id="mock-sol-001",
        ))
        db.commit()

        # Keep provider selection and revalidation real; bypass only the
        # unrelated ingestion fixture so the seeded tracked offer is reached.
        monkeypatch.setattr(
            hotels_service.HotelIngestionService,
            "ingest",
            lambda self: SimpleNamespace(hotels_processed=0),
        )
        result = hotels_service.run_hotel_sweep(db, provider="mock")

        assert result.status == "completed"
        assert result.tracked_outcomes is not None
        assert result.tracked_outcomes["provider_fetch_attempted"] >= 1
        assert result.tracked_outcomes["snapshots_created"] >= 1
        db.refresh(offer)
        assert float(offer.current_price) == 250.00  # type: ignore[arg-type]
    finally:
        _close(db)


@pytest.mark.parametrize(
    ("profile", "expected_status", "expected_warning", "needs_review"),
    [
        ("hotel_ambiguous", "partial", "hotel_ambiguous", True),
        ("stale_history", "completed", "stale_history", True),
        ("partial_batch", "partial", "partial_batch", True),
    ],
)
def test_run_hotel_sweep_persists_advanced_profile_warnings(
    monkeypatch, profile, expected_status, expected_warning, needs_review
) -> None:
    _enable(monkeypatch)
    monkeypatch.setenv("HOTEL_MOCK_FAULT_PROFILE", profile)

    db = _db()
    try:
        user = User(email=f"h44-advanced-{profile}@example.test", password_hash="hash")
        hotel = HotelProperty(
            canonical_name="Hotel Sol Madrid",
            normalized_name="hotel sol madrid",
            city="Madrid",
            normalized_city="madrid",
            country_code="ES",
            latitude=40.4169,
            longitude=-3.7036,
            stars=4,
        )
        db.add_all([user, hotel])
        db.flush()
        offer = create_tracked_offer(
            db,
            user_id=user.id,
            hotel_id=hotel.id,
            check_in=date(2026, 7, 10),
            check_out=date(2026, 7, 12),
            guests=2,
            provider="mock",
            initial_price=250.00,
            currency="EUR",
        )
        db.add(HotelProviderAlias(
            hotel_id=hotel.id,
            provider="mock",
            provider_hotel_id="mock-sol-001",
        ))
        db.commit()

        result = hotels_service.run_hotel_sweep(db, provider="mock")

        assert result.status == expected_status
        assert result.tracked_outcomes is not None
        assert result.tracked_outcomes["warning_count"] >= 1
        assert result.tracked_outcomes["needs_review"] is needs_review
        assert result.tracked_outcomes["fault_profile"] == profile
        warnings = result.tracked_outcomes["warnings"]
        assert any(expected_warning in warning["codes"] for warning in warnings)
        assert result.tracked_outcomes["provider_fetch_attempted"] >= 1
        assert result.tracked_outcomes["snapshots_created"] >= 1
        if profile == "stale_history":
            db.refresh(offer)
            assert float(offer.current_price) == 250.00  # type: ignore[arg-type]
    finally:
        _close(db)


def test_run_hotel_sweep_marks_provider_failure_as_failed(monkeypatch) -> None:
    _enable(monkeypatch)

    class Adapter:
        provider_id = "mock"

        def is_enabled(self):
            return True

    adapter = Adapter()
    monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: adapter)
    monkeypatch.setattr(
        hotels_service.HotelIngestionService,
        "ingest",
        lambda self: SimpleNamespace(hotels_processed=1),
    )
    monkeypatch.setattr(hotels_service, "evaluate_hotel_alerts", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        hotels_service,
        "sweep_tracked_offers",
        lambda *args, **kwargs: {
            "offers_scanned": 1,
            "snapshots_created": 0,
            "provider_fetch_attempted": 1,
            "provider_fetch_completed": 0,
            "provider_fetch_empty": 0,
            "provider_fetch_failed": 1,
            "provider_fetch_skipped": 0,
            "provider_fetch_budget_denied": 0,
        },
    )

    db = _db()
    try:
        result = hotels_service.run_hotel_sweep(db, provider="mock")
        assert result.status == "failed"
        assert result.tracked_outcomes is not None
        assert result.tracked_outcomes["provider_fetch_failed"] == 1
    finally:
        _close(db)


def test_run_hotel_sweep_marks_partial_when_some_tracking_snapshots_exist(monkeypatch) -> None:
    _enable(monkeypatch)

    class Adapter:
        provider_id = "mock"

        def is_enabled(self):
            return True

    adapter = Adapter()
    monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: adapter)
    monkeypatch.setattr(
        hotels_service.HotelIngestionService,
        "ingest",
        lambda self: SimpleNamespace(hotels_processed=1),
    )
    monkeypatch.setattr(hotels_service, "evaluate_hotel_alerts", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        hotels_service,
        "sweep_tracked_offers",
        lambda *args, **kwargs: {
            "offers_scanned": 2,
            "snapshots_created": 1,
            "provider_fetch_attempted": 2,
            "provider_fetch_completed": 1,
            "provider_fetch_empty": 0,
            "provider_fetch_failed": 0,
            "provider_fetch_skipped": 1,
            "provider_fetch_budget_denied": 0,
        },
    )

    db = _db()
    try:
        result = hotels_service.run_hotel_sweep(db, provider="mock")
        assert result.status == "partial"
        assert result.tracked_outcomes is not None
        assert result.tracked_outcomes["snapshots_created"] == 1
    finally:
        _close(db)


def test_run_hotel_sweep_marks_mapping_skip_as_skipped(monkeypatch) -> None:
    _enable(monkeypatch)

    class Adapter:
        provider_id = "mock"

        def is_enabled(self):
            return True

    adapter = Adapter()
    monkeypatch.setattr("app.hotels.ingestion.resolve_hotel_provider", lambda provider: adapter)
    monkeypatch.setattr(
        hotels_service.HotelIngestionService,
        "ingest",
        lambda self: SimpleNamespace(hotels_processed=1),
    )
    monkeypatch.setattr(hotels_service, "evaluate_hotel_alerts", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        hotels_service,
        "sweep_tracked_offers",
        lambda *args, **kwargs: {
            "offers_scanned": 1,
            "snapshots_created": 0,
            "provider_fetch_attempted": 0,
            "provider_fetch_completed": 0,
            "provider_fetch_empty": 0,
            "provider_fetch_failed": 0,
            "provider_fetch_skipped": 1,
            "provider_fetch_budget_denied": 0,
        },
    )

    db = _db()
    try:
        result = hotels_service.run_hotel_sweep(db, provider="mock")
        assert result.status == "skipped"
        assert result.tracked_outcomes is not None
        assert result.tracked_outcomes["provider_fetch_skipped"] == 1
    finally:
        _close(db)
