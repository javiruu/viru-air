from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import pytest

from app.hotels.geo import HotelGeoService, haversine_km
from app.infrastructure.db.models import Base, HotelCompSet, HotelCompSetMember, HotelProperty


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


def _hotel(
    db: Session,
    *,
    name: str,
    city: str,
    country_code: str = "ES",
    latitude: float | None = None,
    longitude: float | None = None,
) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=name,
        normalized_name=name.lower(),
        city=city,
        country_code=country_code,
        latitude=latitude,
        longitude=longitude,
    )
    db.add(hotel)
    db.flush()
    return hotel


def _comp_set(db: Session, *, user_id: str, anchor_hotel_id: str) -> HotelCompSet:
    comp_set = HotelCompSet(user_id=user_id, name="Comp set test", anchor_hotel_id=anchor_hotel_id)
    db.add(comp_set)
    db.flush()
    return comp_set


def test_haversine_km_returns_small_distance_for_close_points() -> None:
    distance = haversine_km(40.4169, -3.7036, 40.4171, -3.7035)
    assert distance > 0
    assert distance < 0.1


def test_geo_service_returns_sorted_suggestions_within_radius() -> None:
    db = _db()
    try:
        anchor = _hotel(db, name="Hotel Sol Madrid", city="Madrid", latitude=40.4169, longitude=-3.7036)
        close = _hotel(db, name="Hotel Luna Madrid", city="Madrid", latitude=40.4171, longitude=-3.7035)
        medium = _hotel(db, name="Hotel Prado", city="Madrid", latitude=40.4205, longitude=-3.7050)
        _hotel(db, name="Hotel Lejano", city="Malaga", latitude=36.7202, longitude=-4.4203)
        comp_set = _comp_set(db, user_id="u1", anchor_hotel_id=anchor.id)

        suggestions = HotelGeoService(db).suggest_for_comp_set(user_id="u1", comp_set_id=comp_set.id, radius_km=2, limit=6)

        assert [item.hotel_id for item in suggestions] == [close.id, medium.id]
        assert suggestions[0].distance_km <= suggestions[1].distance_km
    finally:
        _close(db)


def test_geo_service_excludes_anchor_and_existing_members() -> None:
    db = _db()
    try:
        anchor = _hotel(db, name="Anchor", city="Madrid", latitude=40.4169, longitude=-3.7036)
        member = _hotel(db, name="Member", city="Madrid", latitude=40.4171, longitude=-3.7035)
        candidate = _hotel(db, name="Candidate", city="Madrid", latitude=40.4180, longitude=-3.7040)
        comp_set = _comp_set(db, user_id="u1", anchor_hotel_id=anchor.id)
        db.add(HotelCompSetMember(comp_set_id=comp_set.id, hotel_id=member.id))
        db.commit()

        suggestions = HotelGeoService(db).suggest_for_comp_set(user_id="u1", comp_set_id=comp_set.id, radius_km=2, limit=6)

        assert [item.hotel_id for item in suggestions] == [candidate.id]
    finally:
        _close(db)


def test_geo_service_ignores_hotels_without_coordinates_and_respects_limit() -> None:
    db = _db()
    try:
        anchor = _hotel(db, name="Anchor", city="Madrid", latitude=40.4169, longitude=-3.7036)
        first = _hotel(db, name="First", city="Madrid", latitude=40.4171, longitude=-3.7035)
        second = _hotel(db, name="Second", city="Madrid", latitude=40.4173, longitude=-3.7034)
        _hotel(db, name="No coords", city="Madrid")
        comp_set = _comp_set(db, user_id="u1", anchor_hotel_id=anchor.id)

        suggestions = HotelGeoService(db).suggest_for_comp_set(user_id="u1", comp_set_id=comp_set.id, radius_km=2, limit=1)

        assert len(suggestions) == 1
        assert suggestions[0].hotel_id == first.id
        assert suggestions[0].hotel_id != second.id
    finally:
        _close(db)


def test_geo_service_returns_empty_when_no_candidates_match_radius() -> None:
    db = _db()
    try:
        anchor = _hotel(db, name="Anchor", city="Madrid", latitude=40.4169, longitude=-3.7036)
        _hotel(db, name="Far", city="Malaga", latitude=36.7202, longitude=-4.4203)
        comp_set = _comp_set(db, user_id="u1", anchor_hotel_id=anchor.id)

        suggestions = HotelGeoService(db).suggest_for_comp_set(user_id="u1", comp_set_id=comp_set.id, radius_km=1, limit=6)

        assert suggestions == []
    finally:
        _close(db)


def test_geo_service_requires_anchor_coordinates() -> None:
    db = _db()
    try:
        anchor = _hotel(db, name="Anchor", city="Madrid")
        _hotel(db, name="Candidate", city="Madrid", latitude=40.4171, longitude=-3.7035)
        comp_set = _comp_set(db, user_id="u1", anchor_hotel_id=anchor.id)

        with pytest.raises(ValueError, match="hotel_comp_set_anchor_missing_coordinates"):
            HotelGeoService(db).suggest_for_comp_set(user_id="u1", comp_set_id=comp_set.id, radius_km=5, limit=6)
    finally:
        _close(db)
