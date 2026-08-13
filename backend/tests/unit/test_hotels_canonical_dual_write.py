from __future__ import annotations

import json
from datetime import date

import pytest
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelProperty,
    HotelProviderAlias,
    HotelRateSnapshot,
    HotelStayOffer,
    HotelTrackedOffer,
    HotelUserStayWatch,
    User,
)
from app.services.hotels_service import create_tracked_offer, delete_tracked_offer


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    session.info["test_engine"] = engine
    return session


def _close(db: Session) -> None:
    engine = db.info["test_engine"]
    assert isinstance(engine, Engine)
    db.close()
    engine.dispose()


def _create_user(db: Session, *, email: str) -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_hotel(db: Session) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name="Hotel Canonical Tracking",
        normalized_name="hotel canonical tracking",
        city="Madrid",
        normalized_city="madrid",
        country_code="ES",
        stars=4,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def _add_mock_alias(db: Session, *, hotel_id: str) -> HotelProviderAlias:
    alias = HotelProviderAlias(
        hotel_id=hotel_id,
        provider="mock",
        provider_hotel_id="mock-canonical-001",
        confidence_score=1,
    )
    db.add(alias)
    db.commit()
    return alias


def _create_offer(
    db: Session,
    *,
    user_id: str,
    hotel_id: str,
    include_legacy_conditions: bool = False,
):
    return create_tracked_offer(
        db,
        user_id=user_id,
        hotel_id=hotel_id,
        check_in=date(2026, 9, 10),
        check_out=date(2026, 9, 13),
        guests=2,
        room_label="Doble" if include_legacy_conditions else None,
        meal_plan="Desayuno incluido" if include_legacy_conditions else None,
        cancellation_policy="Cancelación gratuita" if include_legacy_conditions else None,
        provider="mock",
        initial_price=180,
        currency="EUR",
    )


def test_disabled_flags_keep_legacy_tracking_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOTEL_CANONICAL_MODEL_ENABLED", raising=False)
    monkeypatch.delenv("HOTEL_CANONICAL_DUAL_WRITE_ENABLED", raising=False)
    db = _db()
    try:
        user = _create_user(db, email="canonical-off@example.com")
        hotel = _create_hotel(db)

        offer = _create_offer(db, user_id=user.id, hotel_id=hotel.id)

        snapshot = db.scalar(
            select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id)
        )
        assert snapshot is not None
        assert snapshot.stay_offer_id is None
        assert db.scalars(select(HotelStayOffer)).all() == []
        assert db.scalars(select(HotelUserStayWatch)).all() == []
    finally:
        _close(db)


def test_enabled_flags_share_canonical_offer_and_keep_watches_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_CANONICAL_MODEL_ENABLED", "true")
    monkeypatch.setenv("HOTEL_CANONICAL_DUAL_WRITE_ENABLED", "true")
    db = _db()
    try:
        first_user = _create_user(db, email="canonical-first@example.com")
        second_user = _create_user(db, email="canonical-second@example.com")
        hotel = _create_hotel(db)
        _add_mock_alias(db, hotel_id=hotel.id)

        first_offer = _create_offer(db, user_id=first_user.id, hotel_id=hotel.id)
        second_offer = _create_offer(db, user_id=second_user.id, hotel_id=hotel.id)

        stay_offers = db.scalars(select(HotelStayOffer)).all()
        watches = db.scalars(select(HotelUserStayWatch)).all()
        first_snapshot = db.scalar(
            select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == first_offer.id)
        )
        second_snapshot = db.scalar(
            select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == second_offer.id)
        )

        assert len(stay_offers) == 1
        assert {watch.user_id for watch in watches} == {first_user.id, second_user.id}
        assert {watch.legacy_tracked_offer_id for watch in watches} == {first_offer.id, second_offer.id}
        assert first_snapshot is not None
        assert second_snapshot is not None
        assert first_snapshot.stay_offer_id == stay_offers[0].id
        assert second_snapshot.stay_offer_id == stay_offers[0].id
        assert first_snapshot.snapshot_outcome == "success"
        assert first_snapshot.price_semantics == "unknown"
        assert json.loads(stay_offers[0].canonical_query_json)["occupancy"]["source"] == "legacy_inferred"
    finally:
        _close(db)


def test_enabled_flags_roll_back_legacy_write_when_alias_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_CANONICAL_MODEL_ENABLED", "true")
    monkeypatch.setenv("HOTEL_CANONICAL_DUAL_WRITE_ENABLED", "true")
    db = _db()
    try:
        user = _create_user(db, email="canonical-alias@example.com")
        hotel = _create_hotel(db)

        with pytest.raises(ValueError, match="canonical_tracking_alias_missing"):
            _create_offer(db, user_id=user.id, hotel_id=hotel.id)
        db.rollback()

        assert db.scalars(select(HotelTrackedOffer)).all() == []
        assert db.scalars(select(HotelStayOffer)).all() == []
        assert db.scalars(select(HotelUserStayWatch)).all() == []
    finally:
        _close(db)


def test_legacy_condition_text_is_not_inferred_into_canonical_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_CANONICAL_MODEL_ENABLED", "true")
    monkeypatch.setenv("HOTEL_CANONICAL_DUAL_WRITE_ENABLED", "true")
    db = _db()
    try:
        user = _create_user(db, email="canonical-conditions@example.com")
        hotel = _create_hotel(db)
        _add_mock_alias(db, hotel_id=hotel.id)

        offer = _create_offer(
            db,
            user_id=user.id,
            hotel_id=hotel.id,
            include_legacy_conditions=True,
        )

        snapshot = db.scalar(
            select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id)
        )
        assert snapshot is not None
        assert snapshot.stay_offer_id is None
        assert db.scalars(select(HotelStayOffer)).all() == []
        assert db.scalars(select(HotelUserStayWatch)).all() == []
    finally:
        _close(db)


def test_deleting_legacy_tracking_removes_private_watch_but_keeps_shared_offer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_CANONICAL_MODEL_ENABLED", "true")
    monkeypatch.setenv("HOTEL_CANONICAL_DUAL_WRITE_ENABLED", "true")
    db = _db()
    try:
        user = _create_user(db, email="canonical-delete@example.com")
        hotel = _create_hotel(db)
        _add_mock_alias(db, hotel_id=hotel.id)
        offer = _create_offer(db, user_id=user.id, hotel_id=hotel.id)

        delete_tracked_offer(db, user_id=user.id, tracked_offer_id=offer.id)

        assert db.scalars(select(HotelUserStayWatch)).all() == []
        assert len(db.scalars(select(HotelStayOffer)).all()) == 1
    finally:
        _close(db)
