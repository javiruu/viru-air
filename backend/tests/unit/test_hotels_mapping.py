from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.hotels.contracts import ProviderHotelRecord
from app.hotels.mapping import HotelMappingService
from app.infrastructure.db.models import Base, HotelProperty


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


def test_mapping_high_score_merges_existing_hotel() -> None:
    db = _db()
    try:
        existing = HotelProperty(
            canonical_name="Hotel Sol Madrid",
            normalized_name="hotel sol madrid",
            city="Madrid",
            country_code="ES",
            latitude=40.4168,
            longitude=-3.7038,
        )
        db.add(existing)
        db.commit()

        service = HotelMappingService(db)
        result = service.map_or_create(
            ProviderHotelRecord(
                provider_hotel_id="mock-1",
                raw_name="Hotel Sol Madrid",
                raw_address="Calle Sol 1",
                city="Madrid",
                country_code="ES",
                latitude=40.4169,
                longitude=-3.7037,
            )
        )

        assert result.matched_existing is True
        assert result.is_ambiguous is False
        assert result.hotel.id == existing.id
        assert result.confidence_score >= HotelMappingService.HIGH_CONFIDENCE_THRESHOLD
    finally:
        _close(db)


def test_mapping_low_score_creates_new_hotel_for_far_coordinates() -> None:
    db = _db()
    try:
        existing = HotelProperty(
            canonical_name="Hotel Sol Madrid",
            normalized_name="hotel sol madrid",
            city="Madrid",
            country_code="ES",
            latitude=40.4168,
            longitude=-3.7038,
        )
        db.add(existing)
        db.commit()

        service = HotelMappingService(db)
        result = service.map_or_create(
            ProviderHotelRecord(
                provider_hotel_id="mock-2",
                raw_name="Hotel Sol Madrid",
                raw_address="Paseo costero",
                city="Malaga",
                country_code="ES",
                latitude=36.7202,
                longitude=-4.4203,
            )
        )

        assert result.matched_existing is False
        assert result.is_ambiguous is False
        assert result.hotel.id != existing.id
        assert result.confidence_score < HotelMappingService.MEDIUM_CONFIDENCE_THRESHOLD
    finally:
        _close(db)


def test_mapping_medium_score_marks_ambiguous_without_auto_merge() -> None:
    db = _db()
    try:
        existing = HotelProperty(
            canonical_name="Hotel Sol Center",
            normalized_name="hotel sol center",
            city="Madrid",
            country_code="ES",
        )
        db.add(existing)
        db.commit()

        service = HotelMappingService(db)
        result = service.map_or_create(
            ProviderHotelRecord(
                provider_hotel_id="mock-3",
                raw_name="Hotel Sol Centro",
                raw_address="Centro",
                city="Madrid",
                country_code="ES",
            )
        )

        assert result.matched_existing is False
        assert result.is_ambiguous is True
        assert result.confidence_score >= HotelMappingService.MEDIUM_CONFIDENCE_THRESHOLD
        assert result.confidence_score < HotelMappingService.HIGH_CONFIDENCE_THRESHOLD
    finally:
        _close(db)
