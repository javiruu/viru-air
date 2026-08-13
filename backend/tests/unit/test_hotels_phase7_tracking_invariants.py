from __future__ import annotations

from datetime import date

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, HotelProperty, User
from app.services.hotels_service import create_tracked_offer, update_tracked_offer


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


def _create_user(db: Session) -> User:
    user = User(email="tracking-invariant@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_hotel(db: Session) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name="Hotel Tracking Invariant",
        normalized_name="hotel tracking invariant",
        city="Madrid",
        normalized_city="madrid",
        country_code="ES",
        stars=4,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def test_rejects_partial_date_context() -> None:
    db = _db()
    try:
        user = _create_user(db)
        hotel = _create_hotel(db)
        with pytest.raises(ValueError, match="tracked_offer_dates_required_together"):
            create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                provider="mock",
                initial_price=120,
            )
    finally:
        _close(db)


def test_rejects_invalid_date_range() -> None:
    db = _db()
    try:
        user = _create_user(db)
        hotel = _create_hotel(db)
        with pytest.raises(ValueError, match="invalid_date_range"):
            create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 3),
                check_out=date(2026, 8, 1),
                provider="mock",
                initial_price=120,
            )
    finally:
        _close(db)


def test_identity_fields_are_immutable_but_price_and_active_state_are_mutable() -> None:
    db = _db()
    try:
        user = _create_user(db)
        hotel = _create_hotel(db)
        offer = create_tracked_offer(
            db,
            user_id=user.id,
            hotel_id=hotel.id,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            provider="mock",
            initial_price=120,
            target_price=100,
            currency="EUR",
        )
        with pytest.raises(ValueError, match="tracked_offer_identity_immutable"):
            update_tracked_offer(
                db,
                user_id=user.id,
                tracked_offer_id=offer.id,
                update_data={"check_in": date(2026, 8, 2)},
            )
        updated = update_tracked_offer(
            db,
            user_id=user.id,
            tracked_offer_id=offer.id,
            update_data={"target_price": 90, "is_active": False},
        )
        assert float(updated.target_price) == 90
        assert updated.is_active is False
    finally:
        _close(db)
