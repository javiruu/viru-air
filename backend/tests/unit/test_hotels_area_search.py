"""Unit tests for hotel area search."""

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelProperty,
    HotelRateSnapshot,
    HotelTrackedOffer,
)
from app.services.hotels_service import area_search, create_tracked_offer


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
    name: str = "Hotel Test",
    city: str = "Madrid",
    country: str = "ES",
    lat: float = 40.4168,
    lng: float = -3.7038,
    stars: int | None = 4,
) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=name,
        normalized_name=name.lower(),
        city=city,
        country_code=country,
        latitude=lat,
        longitude=lng,
        stars=stars,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def _create_rate(
    db: Session,
    *,
    hotel_id: str,
    check_in: date,
    check_out: date,
    guests: int = 2,
    currency: str = "EUR",
    amount: float,
    provider: str = "mock",
) -> HotelRateSnapshot:
    rate = HotelRateSnapshot(
        hotel_id=hotel_id,
        provider=provider,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        currency=currency,
        amount=amount,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


def test_area_search_finds_hotels_within_radius() -> None:
    db = _db()
    try:
        # Madrid center ~ 40.4168, -3.7038
        h1 = _create_hotel(db, name="Hotel Sol", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Hotel Retiro", lat=40.4200, lng=-3.6900)
        h3 = _create_hotel(db, name="Hotel Barcelona", city="Barcelona", lat=41.3874, lng=2.1686)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=120.00)
        _create_rate(db, hotel_id=h3.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=200.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id in result_ids
        assert h2.id in result_ids
        assert h3.id not in result_ids  # Barcelona is far away
        assert len(results) == 2
    finally:
        _close(db)


def test_area_search_returns_lowest_price_per_hotel() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel Sol", lat=40.4168, lng=-3.7038)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00, provider="mock")
        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=85.00, provider="booking")
        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=95.00, provider="makcorps")

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert len(results) == 1
        assert results[0]["lowest_price"] == 85.00
        assert results[0]["provider"] == "booking"
    finally:
        _close(db)


def test_area_search_empty_when_no_hotels_in_radius() -> None:
    db = _db()
    try:
        _create_hotel(db, name="Hotel Sol", lat=40.4168, lng=-3.7038)

        results = area_search(
            db,
            latitude=41.3874,
            longitude=2.1686,
            radius_km=1,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert results == []
    finally:
        _close(db)


def test_area_search_filters_by_min_stars() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel 3*", lat=40.4168, lng=-3.7038, stars=3)
        h2 = _create_hotel(db, name="Hotel 4*", lat=40.4200, lng=-3.6900, stars=4)
        h3 = _create_hotel(db, name="Hotel 5*", lat=40.4150, lng=-3.7000, stars=5)

        for h in [h1, h2, h3]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            min_stars=4,
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id not in result_ids
        assert h2.id in result_ids
        assert h3.id in result_ids
        assert len(results) == 2
    finally:
        _close(db)


def test_area_search_filters_by_max_price() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Cheap", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Expensive", lat=40.4200, lng=-3.6900)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=80.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=150.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            max_price=100.00,
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id in result_ids
        assert h2.id not in result_ids
        assert len(results) == 1
    finally:
        _close(db)


def test_area_search_sorts_by_price() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel A", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Hotel B", lat=40.4200, lng=-3.6900)
        h3 = _create_hotel(db, name="Hotel C", lat=40.4150, lng=-3.7000)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=50.00)
        _create_rate(db, hotel_id=h3.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=75.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            sort="price",
        )

        assert len(results) == 3
        assert results[0]["lowest_price"] == 50.00
        assert results[1]["lowest_price"] == 75.00
        assert results[2]["lowest_price"] == 100.00
    finally:
        _close(db)


def test_area_search_sorts_by_distance() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel Far", lat=40.4300, lng=-3.7100)
        h2 = _create_hotel(db, name="Hotel Near", lat=40.4170, lng=-3.7040)
        h3 = _create_hotel(db, name="Hotel Mid", lat=40.4200, lng=-3.7000)

        for h in [h1, h2, h3]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            sort="distance",
        )

        assert len(results) == 3
        assert results[0]["hotel_id"] == h2.id  # nearest
        assert results[0]["distance_km"] <= results[1]["distance_km"]
        assert results[1]["distance_km"] <= results[2]["distance_km"]
    finally:
        _close(db)


def test_area_search_sorts_by_stars() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Hotel 3*", lat=40.4168, lng=-3.7038, stars=3)
        h2 = _create_hotel(db, name="Hotel 5*", lat=40.4200, lng=-3.6900, stars=5)
        h3 = _create_hotel(db, name="Hotel 4*", lat=40.4150, lng=-3.7000, stars=4)

        for h in [h1, h2, h3]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            sort="stars",
        )

        assert len(results) == 3
        assert results[0]["stars"] == 5
        assert results[1]["stars"] == 4
        assert results[2]["stars"] == 3
    finally:
        _close(db)


def test_area_search_has_tracking_flag() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="Tracked Hotel", lat=40.4168, lng=-3.7038)
        h2 = _create_hotel(db, name="Untracked Hotel", lat=40.4200, lng=-3.6900)

        for h in [h1, h2]:
            _create_rate(db, hotel_id=h.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        create_tracked_offer(db, user_id="user-track", hotel_id=h1.id, provider="mock", initial_price=100.00, currency="EUR")

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            user_id="user-track",
        )

        h1_result = next(r for r in results if r["hotel_id"] == h1.id)
        h2_result = next(r for r in results if r["hotel_id"] == h2.id)
        assert h1_result["has_tracking"] is True
        assert h2_result["has_tracking"] is False
    finally:
        _close(db)


def test_area_search_hotel_without_rates_shows_no_price() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="No Rates Hotel", lat=40.4168, lng=-3.7038)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        assert len(results) == 1
        assert results[0]["lowest_price"] is None
        assert results[0]["provider"] is None
    finally:
        _close(db)


def test_area_search_respects_currency_filter() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="EUR Hotel", lat=40.4168, lng=-3.7038)

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00, currency="EUR")
        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=85.00, currency="USD")

        results_eur = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        results_usd = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="USD",
        )

        assert results_eur[0]["lowest_price"] == 100.00
        assert results_usd[0]["lowest_price"] == 85.00
    finally:
        _close(db)


def test_area_search_excludes_hotels_without_coordinates() -> None:
    db = _db()
    try:
        h1 = _create_hotel(db, name="With Coords", lat=40.4168, lng=-3.7038)
        h2 = HotelProperty(
            canonical_name="No Coords",
            normalized_name="no coords",
            city="Madrid",
            country_code="ES",
            latitude=None,
            longitude=None,
            stars=4,
        )
        db.add(h2)
        db.commit()

        _create_rate(db, hotel_id=h1.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)
        _create_rate(db, hotel_id=h2.id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 3), amount=100.00)

        results = area_search(
            db,
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=50,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
        )

        result_ids = {r["hotel_id"] for r in results}
        assert h1.id in result_ids
        assert h2.id not in result_ids
    finally:
        _close(db)
