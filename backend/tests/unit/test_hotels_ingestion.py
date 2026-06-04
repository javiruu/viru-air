from pathlib import Path
import json

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.hotels.ingestion import HotelIngestionService, resolve_hotel_provider
from app.infrastructure.db.models import Base, HotelProperty, HotelProviderAlias, HotelRateSnapshot
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


def test_resolve_hotel_provider_is_disabled_by_default_outside_local_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOTEL_FEATURE_ENABLED", raising=False)
    monkeypatch.delenv("HOTEL_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError, match="ingestion and sweeps are disabled"):
        resolve_hotel_provider()


def test_resolve_hotel_provider_uses_mock_by_default_in_local_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOTEL_FEATURE_ENABLED", raising=False)
    monkeypatch.delenv("HOTEL_PROVIDER", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    provider = resolve_hotel_provider()

    assert provider.provider_id == "mock"


def test_resolve_hotel_provider_uses_mock_when_feature_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.delenv("HOTEL_PROVIDER", raising=False)
    provider = resolve_hotel_provider()
    assert provider.provider_id == "mock"


def test_resolve_hotel_provider_rejects_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="Unsupported hotel provider"):
        resolve_hotel_provider()


def test_ingestion_loads_fixtures_and_persists_aliases_and_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_path = Path(__file__).resolve().parents[2] / "app" / "hotels" / "fixtures" / "mock_hotels.json"
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    monkeypatch.setenv("HOTEL_MOCK_FIXTURE_PATH", str(fixture_path))

    db = _db()
    try:
        result = HotelIngestionService(db).ingest()

        assert result.provider_id == "mock"
        assert result.hotels_processed == 3
        assert result.rates_ingested == 3

        aliases = db.scalars(select(HotelProviderAlias)).all()
        rates = db.scalars(select(HotelRateSnapshot)).all()
        assert len(aliases) == 3
        assert len(rates) == 3
        assert {rate.currency for rate in rates} == {"EUR"}
        assert all(alias.raw_payload is not None for alias in aliases)

        # Idempotencia razonable: segunda ingesta no duplica rates.
        second = HotelIngestionService(db).ingest()
        assert second.rates_ingested == 0
        assert len(db.scalars(select(HotelProviderAlias)).all()) == 3
        assert len(db.scalars(select(HotelRateSnapshot)).all()) == 3
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
