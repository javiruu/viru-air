"""Unit tests for hotel area resolve."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, HotelProperty
from app.services.hotels_service import area_resolve


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


def _create_hotel(
    db: Session,
    *,
    name: str,
    city: str,
    country: str = "ES",
    lat: float = 40.4168,
    lng: float = -3.7038,
) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=name,
        normalized_name=name.lower(),
        city=city,
        normalized_city=city.lower(),
        country_code=country,
        latitude=lat,
        longitude=lng,
        stars=4,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def test_area_resolve_madrid_returns_centroid() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Sol", city="Madrid", lat=40.4169, lng=-3.7036)
        _create_hotel(db, name="Hotel Luna", city="Madrid", lat=40.4171, lng=-3.7035)

        result = area_resolve(db, q="Madrid")

        assert result["area_label"] == "Madrid"
        assert result["country_code"] == "ES"
        assert 40.41 <= float(result["latitude"]) <= 40.42  # type: ignore[arg-type]
        assert -3.71 <= float(result["longitude"]) <= -3.70  # type: ignore[arg-type]
        assert result["confidence"] == "medium"
        assert result["source"] == "internal"
    finally:
        _close(db)


def test_area_resolve_single_hotel_low_confidence() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Malaga", city="Malaga", lat=36.7202, lng=-4.4203)

        result = area_resolve(db, q="Malaga")

        assert result["area_label"] == "Malaga"
        assert result["latitude"] == 36.7202
        assert result["longitude"] == -4.4203
        assert result["confidence"] == "low"
        assert result["source"] == "internal"
    finally:
        _close(db)


def test_area_resolve_multiple_hotels_high_confidence() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel A", city="Barcelona", lat=41.3874, lng=2.1686)
        _create_hotel(db, name="Hotel B", city="Barcelona", lat=41.3900, lng=2.1700)
        _create_hotel(db, name="Hotel C", city="Barcelona", lat=41.3850, lng=2.1650)

        result = area_resolve(db, q="Barcelona")

        assert result["area_label"] == "Barcelona"
        assert result["confidence"] == "high"
        assert result["source"] == "internal"
    finally:
        _close(db)


def test_area_resolve_case_insensitive() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Sol", city="Madrid", lat=40.4169, lng=-3.7036)

        result = area_resolve(db, q="madrid")

        assert result["area_label"] == "Madrid"
    finally:
        _close(db)


def test_area_resolve_partial_city_match() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Sol", city="Madrid Centro", lat=40.4169, lng=-3.7036)

        result = area_resolve(db, q="Madrid")

        assert result["area_label"] == "Madrid Centro"
    finally:
        _close(db)


def test_area_resolve_not_found_raises_error() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Sol", city="Madrid", lat=40.4169, lng=-3.7036)

        with pytest.raises(ValueError, match="area_not_found"):
            area_resolve(db, q="Tokyo")
    finally:
        _close(db)


def test_area_resolve_ignores_hotels_without_coordinates() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Sol", city="Madrid", lat=40.4169, lng=-3.7036)
        # Hotel without coordinates should be ignored
        db.add(
            HotelProperty(
                canonical_name="No Coordinates",
                normalized_name="no coordinates",
                city="Madrid",
                normalized_city="madrid",
                country_code="ES",
                latitude=None,
                longitude=None,
                stars=4,
            )
        )
        db.commit()

        result = area_resolve(db, q="Madrid")

        assert result["latitude"] == 40.4169
        assert result["longitude"] == -3.7036
        assert result["confidence"] == "low"  # only 1 hotel with coords
    finally:
        _close(db)


def test_area_resolve_empty_db_raises_error() -> None:
    db = _db()
    try:
        with pytest.raises(ValueError, match="area_not_found"):
            area_resolve(db, q="Madrid")
    finally:
        _close(db)


def test_area_resolve_mixed_countries_uses_most_common() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel ES", city="TestCity", country="ES", lat=40.0, lng=-3.0)
        _create_hotel(db, name="Hotel ES 2", city="TestCity", country="ES", lat=40.01, lng=-3.01)

        result = area_resolve(db, q="TestCity")

        assert result["country_code"] == "ES"
        assert result["confidence"] == "medium"
    finally:
        _close(db)
