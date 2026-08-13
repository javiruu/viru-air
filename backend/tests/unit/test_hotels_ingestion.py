from pathlib import Path
import json

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.hotels.ingestion import HotelIngestionService, resolve_hotel_provider
from app.infrastructure.db.models import (
    Base,
    HotelProperty,
    HotelProviderAlias,
    HotelProviderRun,
    HotelRateSnapshot,
)
from app.hotels.contracts import ProviderHotelRecord
from app.services.hotels_service import run_hotel_sweep


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def _close(db: Session) -> None:
    engine = db._test_engine  # type: ignore[attr-defined]
    db.close()
    engine.dispose()


@pytest.fixture(autouse=True)
def _local_hotel_test_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")


def test_resolve_hotel_provider_is_disabled_by_default_outside_local_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOTEL_FEATURE_ENABLED", raising=False)
    monkeypatch.delenv("HOTEL_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError, match="ingestion and sweeps are disabled"):
        resolve_hotel_provider()


def test_resolve_hotel_provider_requires_explicit_feature_in_local_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOTEL_FEATURE_ENABLED", raising=False)
    monkeypatch.delenv("HOTEL_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    with pytest.raises(ValueError, match="ingestion and sweeps are disabled"):
        resolve_hotel_provider()


def test_resolve_hotel_provider_uses_mock_when_feature_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.delenv("HOTEL_PROVIDER", raising=False)
    provider = resolve_hotel_provider()
    assert provider.provider_id == "mock"


def test_resolve_hotel_provider_rejects_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "unknown")
    monkeypatch.setenv("HOTEL_PROVIDER_UNKNOWN_ENABLED", "true")
    with pytest.raises(ValueError, match="Unsupported hotel provider"):
        resolve_hotel_provider()


def test_explicit_mock_ingestion_ignores_configured_external_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")

    from app.hotels import ingestion
    from app.services import hotels_service

    def unexpected_provider_resolution():
        raise AssertionError("explicit mock ingestion must not resolve HOTEL_PROVIDER")

    monkeypatch.setattr(ingestion, "resolve_hotel_provider", unexpected_provider_resolution)
    db = _db()
    try:
        result = hotels_service.ingest_hotels_mock(db)

        assert result.provider_id == "mock"
    finally:
        _close(db)


def test_ingestion_loads_fixtures_and_persists_aliases_and_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_path = Path(__file__).resolve().parents[2] / "app" / "hotels" / "fixtures" / "mock_hotels.json"
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    monkeypatch.setenv("HOTEL_MOCK_FIXTURE_PATH", str(fixture_path))

    db = _db()
    try:
        samples = []
        result = HotelIngestionService(db, latency_sink=samples.append).ingest()

        assert result.provider_id == "mock"
        assert len(samples) == 1
        assert samples[0].operation == "ingestion"
        assert samples[0].provider == "mock"
        assert samples[0].outcome == "success"
        assert samples[0].duration_ms >= 0
        assert result.hotels_processed == 3
        assert result.rates_ingested == 3

        aliases = db.scalars(select(HotelProviderAlias)).all()
        rates = db.scalars(select(HotelRateSnapshot)).all()
        # Ambiguous matches remain persisted as zero-confidence review markers,
        # never as confirmed provider identities.
        assert len(aliases) == 3
        assert len(rates) == 3
        assert {rate.currency for rate in rates} == {"EUR"}
        assert all(rate.provider_run_id is None for rate in rates)
        assert all(alias.raw_payload is not None for alias in aliases)

        # Idempotencia razonable: segunda ingesta no duplica rates.
        second = HotelIngestionService(db).ingest()
        assert second.rates_ingested == 0
        assert len(db.scalars(select(HotelProviderAlias)).all()) == 3
        assert len(db.scalars(select(HotelRateSnapshot)).all()) == 3
    finally:
        _close(db)


def test_ingestion_records_advanced_profile_warnings_and_review(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")

    from app.hotels.mock_provider import MockHotelProviderAdapter

    for profile, expected_code in (("hotel_ambiguous", "hotel_ambiguous"), ("stale_history", "stale_history"), ("partial_batch", "partial_batch")):
        db = _db()
        try:
            result = HotelIngestionService(
                db,
                provider=MockHotelProviderAdapter(fault_profile=profile),
            ).ingest()
            assert result.warnings
            assert result.needs_review is True
            assert result.fault_profile == profile
            assert all(expected_code in warning["codes"] for warning in result.warnings)
            assert all(item.warnings for item in result.items)
            if profile == "hotel_ambiguous":
                assert db.query(HotelProviderAlias).count() == 3
                assert db.query(HotelProviderAlias).filter(
                    HotelProviderAlias.confidence_score == 0
                ).count() == 3
            if profile == "stale_history":
                # Freshness alone is not a review gate; genuine mapping
                # ambiguity still is, even while the stale profile is active.
                assert all(item.needs_review is item.is_ambiguous for item in result.items)
                assert result.needs_review is any(item.is_ambiguous for item in result.items)
        finally:
            _close(db)


def test_ingestion_emits_empty_latency_sample_for_empty_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")

    class EmptyProvider:
        provider_id = "mock"

        def is_enabled(self) -> bool:
            return True

        def fetch_hotels(self) -> list[ProviderHotelRecord]:
            return []

    db = _db()
    try:
        samples = []
        result = HotelIngestionService(db, provider=EmptyProvider(), latency_sink=samples.append).ingest()
        assert result.hotels_processed == 0
        assert len(samples) == 1
        assert samples[0].operation == "ingestion"
        assert samples[0].outcome == "empty"
    finally:
        _close(db)


def test_external_ingestion_budget_zero_skips_adapter_before_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.delenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", raising=False)

    class UnexpectedProvider:
        provider_id = "makcorps"

        def is_enabled(self) -> bool:
            return True

        def fetch_hotels(self) -> list[ProviderHotelRecord]:
            raise AssertionError("budget denial must happen before ingestion adapter call")

    db = _db()
    try:
        with pytest.raises(ValueError, match="hotel_provider_budget_denied"):
            HotelIngestionService(db, provider=UnexpectedProvider()).ingest()
        assert db.query(HotelProviderAlias).count() == 0
    finally:
        _close(db)


def test_ingestion_rejects_invalid_currency_and_date_range(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = {
        "hotels": [
            {
                "provider_hotel_id": "mock-bad-001",
                "name": "Hotel Error",
                "address": "Calle Falsa 1",
                "city": "Madrid",
                "country_code": "ES",
                "rates": [
                    {
                        "check_in": "2026-07-12",
                        "check_out": "2026-07-10",
                        "amount": 120,
                        "currency": "EURO",
                    }
                ],
            }
        ]
    }
    fixture_path = tmp_path / "invalid_hotels.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    monkeypatch.setenv("HOTEL_MOCK_FIXTURE_PATH", str(fixture_path))

    db = _db()
    try:
        with pytest.raises(ValueError, match="Invalid currency|Invalid stay range"):
            HotelIngestionService(db).ingest()
    finally:
        _close(db)


def test_mock_ingest_failure_rolls_back_partial_observations_and_keeps_failed_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")

    db = _db()
    try:
        from app.services import hotels_service

        class PartialFailureIngestion:
            def __init__(self, session, **kwargs):
                self.session = session

            def ingest(self):
                hotel = HotelProperty(
                    canonical_name="Partial hotel",
                    normalized_name="partial hotel",
                    city="Madrid",
                    country_code="ES",
                )
                self.session.add(hotel)
                self.session.flush()
                self.session.add(
                    HotelProviderAlias(
                        hotel_id=hotel.id,
                        provider="mock",
                        provider_hotel_id="partial-1",
                    )
                )
                self.session.add(
                    HotelRateSnapshot(
                        hotel_id=hotel.id,
                        provider="mock",
                        check_in=date(2026, 8, 1),
                        check_out=date(2026, 8, 3),
                        guests=2,
                        currency="EUR",
                        amount=100,
                    )
                )
                self.session.flush()
                raise RuntimeError("provider failed after partial work")

        monkeypatch.setattr(hotels_service, "HotelIngestionService", PartialFailureIngestion)

        with pytest.raises(RuntimeError, match="provider failed after partial work"):
            hotels_service.ingest_hotels_mock(db)

        assert db.query(HotelProperty).count() == 0
        assert db.query(HotelProviderAlias).count() == 0
        assert db.query(HotelRateSnapshot).count() == 0
        failed_run = db.query(HotelProviderRun).one()
        assert failed_run.status == "failed"
    finally:
        _close(db)


def test_run_hotel_sweep_links_each_ingestion_observation_to_its_provider_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_SWEEP_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    db = _db()
    try:
        samples = []
        first = run_hotel_sweep(db, provider="mock", latency_sink=samples.append)
        second = run_hotel_sweep(db, provider="mock")

        assert first.status == "completed"
        assert len(samples) == 1
        assert samples[0].operation == "ingestion"
        assert samples[0].provider == "mock"
        assert second.status == "completed"
        rates = db.scalars(select(HotelRateSnapshot)).all()
        assert len(rates) == 6
        assert {rate.provider_run_id for rate in rates} == {first.id, second.id}
        assert sum(rate.provider_run_id == first.id for rate in rates) == 3
        assert sum(rate.provider_run_id == second.id for rate in rates) == 3

        # Replaying the same provider run remains idempotent.
        replay = HotelIngestionService(db, provider_run_id=second.id).ingest()
        assert replay.rates_ingested == 0
        assert len(db.scalars(select(HotelRateSnapshot)).all()) == 6
    finally:
        _close(db)


def test_run_hotel_sweep_fails_cleanly_when_feature_flag_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "false")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")

    db = _db()
    try:
        provider_run = run_hotel_sweep(db, provider="mock")
        assert provider_run.status == "failed"
        assert provider_run.error_message is not None
        assert "HOTEL_FEATURE_ENABLED" in provider_run.error_message
    finally:
        _close(db)


def test_read_paths_can_use_existing_data_even_when_feature_flag_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "false")

    db = _db()
    try:
        hotel = HotelProperty(
            canonical_name="Hotel Persistido",
            normalized_name="hotel persistido",
            city="Madrid",
            country_code="ES",
            stars=4,
        )
        db.add(hotel)
        db.flush()
        db.add(
            HotelRateSnapshot(
                hotel_id=hotel.id,
                provider="mock",
                check_in=date(2026, 7, 1),
                check_out=date(2026, 7, 3),
                guests=2,
                currency="EUR",
                amount=150,
            )
        )
        db.commit()

        persisted_hotel = db.get(HotelProperty, hotel.id)
        persisted_rates = db.scalars(select(HotelRateSnapshot).where(HotelRateSnapshot.hotel_id == hotel.id)).all()
        assert persisted_hotel is not None
        assert len(persisted_rates) == 1
    finally:
        _close(db)
