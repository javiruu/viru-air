from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.hotels.mapping import HotelMappingService
from app.hotels.contracts import ProviderHotelRecord, ProviderRateRecord
from app.hotels.normalization import HotelNormalizationService
from app.infrastructure.db.models import Base, HotelProperty
from app.services.hotels_service import search_hotels


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


def test_normalize_text_handles_case_accents_punctuation_and_spaces() -> None:
    value = "  HOTEL Sol,  Madrid!!!  "
    assert HotelNormalizationService.normalize_text(value) == "hotel sol madrid"


def test_normalize_text_collapses_tabs_dashes_and_symbols_into_stable_tokens() -> None:
    value = "\tHôtel-Sol & Spa\nMadrid  "
    assert HotelNormalizationService.normalize_text(value) == "hotel sol spa madrid"


def test_normalize_city_and_country_are_stable() -> None:
    assert HotelNormalizationService.normalize_city("Malaga") == "malaga"
    assert HotelNormalizationService.normalize_country_code(" es ") == "ES"


def test_normalize_text_handles_empty_values_without_noise() -> None:
    assert HotelNormalizationService.normalize_text(None) == ""
    assert HotelNormalizationService.normalize_text("   ") == ""


def test_search_hotels_matches_city_without_accents() -> None:
    db = _db()
    try:
        db.add(
            HotelProperty(
                canonical_name="Hotel Malaga Centro",
                normalized_name="hotel malaga centro",
                city="Malaga",
                normalized_city="malaga",
                country_code="ES",
                stars=4,
            )
        )
        db.commit()

        rows = search_hotels(db, q=None, city="Málaga", country_code=None, limit=20, offset=0)
        assert len(rows) == 1
        assert rows[0].canonical_name == "Hotel Malaga Centro"
    finally:
        _close(db)


def test_search_hotels_matches_city_case_insensitive_and_without_accents() -> None:
    db = _db()
    try:
        db.add(
            HotelProperty(
                canonical_name="Hotel Cordoba Ribera",
                normalized_name="hotel cordoba ribera",
                city="Cordoba",
                normalized_city="cordoba",
                country_code="ES",
                stars=4,
            )
        )
        db.commit()

        rows = search_hotels(db, q=None, city="cÓRDoBa", country_code=None, limit=20, offset=0)
        assert len(rows) == 1
        assert rows[0].canonical_name == "Hotel Cordoba Ribera"
    finally:
        _close(db)


def test_search_hotels_does_not_filter_when_city_normalizes_to_empty() -> None:
    db = _db()
    try:
        db.add(
            HotelProperty(
                canonical_name="Hotel Madrid Centro",
                normalized_name="hotel madrid centro",
                city="Madrid",
                normalized_city="madrid",
                country_code="ES",
                stars=4,
            )
        )
        db.commit()

        rows = search_hotels(db, q=None, city="   ", country_code=None, limit=20, offset=0)
        assert len(rows) == 1
    finally:
        _close(db)


def test_mapping_service_persists_normalized_city_on_create() -> None:
    db = _db()
    try:
        record = ProviderHotelRecord(
            provider_hotel_id="mock-mlg-001",
            raw_name="Hotel Malaga Costa",
            raw_address="Paseo Maritimo 1",
            city="Málaga",
            country_code="es",
            latitude=None,
            longitude=None,
            stars=4,
            rates=[
                ProviderRateRecord(
                    check_in=date(2026, 7, 1),
                    check_out=date(2026, 7, 3),
                    amount=120.0,
                    currency="EUR",
                    room_label=None,
                    meal_plan=None,
                    cancellation_policy=None,
                    guests=2,
                )
            ],
        )

        result = HotelMappingService(db).map_or_create(record)
        assert result.hotel.normalized_city == HotelNormalizationService.normalize_city("Málaga")
    finally:
        _close(db)
