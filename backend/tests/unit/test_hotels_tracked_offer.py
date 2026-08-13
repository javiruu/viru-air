"""Unit tests for HotelTrackedOffer CRUD operations and snapshot tracking."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelProperty,
    HotelRateSnapshot,
    HotelTrackedOffer,
)
from app.services.hotels_service import (
    create_tracked_offer,
    delete_tracked_offer,
    get_tracked_offer_or_404,
    list_tracked_offer_snapshots,
    list_tracked_offers,
    update_tracked_offer,
)


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


def _create_hotel(db: Session, *, name: str = "Hotel Test") -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=name,
        normalized_name=name.lower(),
        city="Madrid",
        country_code="ES",
        stars=4,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def test_create_tracked_offer_persists_all_fields() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        user_id = "user-001"

        offer = create_tracked_offer(
            db,
            user_id=user_id,
            hotel_id=hotel.id,
            area_label="Madrid Centro",
            origin_query="Madrid",
            latitude=40.4168,
            longitude=-3.7038,
            radius_km=5,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            room_label="Habitación doble",
            meal_plan="Desayuno incluido",
            cancellation_policy="Cancelación gratuita",
            provider="booking",
            initial_price=120.50,
            target_price=100.00,
            currency="EUR",
        )

        assert offer.id is not None
        assert offer.user_id == user_id
        assert offer.hotel_id == hotel.id
        assert offer.area_label == "Madrid Centro"
        assert offer.origin_query == "Madrid"
        assert float(offer.latitude) == 40.4168  # type: ignore[arg-type]
        assert float(offer.longitude) == -3.7038  # type: ignore[arg-type]
        assert offer.radius_km == 5
        assert offer.check_in == date(2026, 8, 1)
        assert offer.check_out == date(2026, 8, 3)
        assert offer.guests == 2
        assert offer.room_label == "Habitación doble"
        assert offer.meal_plan == "Desayuno incluido"
        assert offer.cancellation_policy == "Cancelación gratuita"
        assert offer.provider == "booking"
        assert float(offer.initial_price) == 120.50  # type: ignore[arg-type]
        assert float(offer.current_price) == 120.50  # type: ignore[arg-type]  # defaults to initial_price
        assert float(offer.target_price) == 100.00  # type: ignore[arg-type]
        assert offer.currency == "EUR"
        assert offer.is_active is True
        assert offer.created_at is not None
        assert offer.updated_at is not None
    finally:
        _close(db)


def test_create_tracked_offer_with_minimal_fields() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        user_id = "user-002"

        offer = create_tracked_offer(
            db,
            user_id=user_id,
            hotel_id=hotel.id,
            provider="mock",
            currency="EUR",
        )

        assert offer.id is not None
        assert offer.user_id == user_id
        assert offer.hotel_id == hotel.id
        assert offer.guests == 2
        assert offer.is_active is True
        assert offer.initial_price is None
        assert offer.current_price is None
        assert offer.target_price is None
    finally:
        _close(db)


def test_create_tracked_offer_rejects_invalid_hotel() -> None:
    db = _db()
    try:
        with pytest.raises(ValueError, match="hotel_not_found"):
            create_tracked_offer(
                db,
                user_id="user-003",
                hotel_id="nonexistent-id",
            )
    finally:
        _close(db)


def test_list_tracked_offers_by_user() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)

        create_tracked_offer(db, user_id="user-a", hotel_id=hotel.id)
        create_tracked_offer(db, user_id="user-a", hotel_id=hotel.id)
        create_tracked_offer(db, user_id="user-b", hotel_id=hotel.id)

        offers_a = list_tracked_offers(db, user_id="user-a")
        offers_b = list_tracked_offers(db, user_id="user-b")

        assert len(offers_a) == 2
        assert len(offers_b) == 1
        assert all(o.user_id == "user-a" for o in offers_a)
        assert all(o.user_id == "user-b" for o in offers_b)
    finally:
        _close(db)


def test_list_tracked_offers_filter_active() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)

        offer1 = create_tracked_offer(db, user_id="user-c", hotel_id=hotel.id)
        offer2 = create_tracked_offer(db, user_id="user-c", hotel_id=hotel.id)

        # Deactivate first offer
        o = db.get(HotelTrackedOffer, offer1.id)
        assert o is not None
        o.is_active = False
        db.commit()

        active = list_tracked_offers(db, user_id="user-c", is_active=True)
        inactive = list_tracked_offers(db, user_id="user-c", is_active=False)

        assert len(active) == 1
        assert active[0].id == offer2.id
        assert len(inactive) == 1
        assert inactive[0].id == offer1.id
    finally:
        _close(db)


def test_get_tracked_offer_by_id() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        created = create_tracked_offer(db, user_id="user-d", hotel_id=hotel.id)

        retrieved = get_tracked_offer_or_404(db, user_id="user-d", tracked_offer_id=created.id)
        assert retrieved.id == created.id
        assert retrieved.user_id == "user-d"
    finally:
        _close(db)


def test_get_tracked_offer_not_found() -> None:
    db = _db()
    try:
        with pytest.raises(ValueError, match="tracked_offer_not_found"):
            get_tracked_offer_or_404(db, user_id="user-e", tracked_offer_id="nonexistent-id")
    finally:
        _close(db)


def test_get_tracked_offer_enforces_ownership() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        created = create_tracked_offer(db, user_id="user-f", hotel_id=hotel.id)

        with pytest.raises(PermissionError, match="not_allowed"):
            get_tracked_offer_or_404(db, user_id="user-g", tracked_offer_id=created.id)
    finally:
        _close(db)


def test_update_tracked_offer() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        created = create_tracked_offer(
            db,
            user_id="user-h",
            hotel_id=hotel.id,
            initial_price=100.00,
            current_price=100.00,
        )

        updated = update_tracked_offer(
            db,
            user_id="user-h",
            tracked_offer_id=created.id,
            update_data={"current_price": 95.00, "target_price": 80.00},
        )

        assert float(updated.current_price) == 95.00  # type: ignore[arg-type]
        assert float(updated.target_price) == 80.00  # type: ignore[arg-type]
        assert float(updated.initial_price) == 100.00  # type: ignore[arg-type]  # unchanged
    finally:
        _close(db)


def test_update_tracked_offer_enforces_ownership() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        created = create_tracked_offer(db, user_id="user-i", hotel_id=hotel.id)

        with pytest.raises(PermissionError, match="not_allowed"):
            update_tracked_offer(
                db,
                user_id="user-j",
                tracked_offer_id=created.id,
                update_data={"current_price": 50.00},
            )
    finally:
        _close(db)


def test_update_tracked_offer_deactivate() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        created = create_tracked_offer(db, user_id="user-k", hotel_id=hotel.id)
        assert created.is_active is True

        updated = update_tracked_offer(
            db,
            user_id="user-k",
            tracked_offer_id=created.id,
            update_data={"is_active": False},
        )

        assert updated.is_active is False
    finally:
        _close(db)


def test_delete_tracked_offer() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        created = create_tracked_offer(db, user_id="user-l", hotel_id=hotel.id)

        delete_tracked_offer(db, user_id="user-l", tracked_offer_id=created.id)

        with pytest.raises(ValueError, match="tracked_offer_not_found"):
            get_tracked_offer_or_404(db, user_id="user-l", tracked_offer_id=created.id)
    finally:
        _close(db)


def test_delete_tracked_offer_enforces_ownership() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        created = create_tracked_offer(db, user_id="user-m", hotel_id=hotel.id)

        with pytest.raises(PermissionError, match="not_allowed"):
            delete_tracked_offer(db, user_id="user-n", tracked_offer_id=created.id)
    finally:
        _close(db)


def test_delete_tracked_offer_not_found() -> None:
    db = _db()
    try:
        with pytest.raises(ValueError, match="tracked_offer_not_found"):
            delete_tracked_offer(db, user_id="user-o", tracked_offer_id="nonexistent-id")
    finally:
        _close(db)


def test_tracked_offer_can_have_separate_initial_and_current_price() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)

        offer = create_tracked_offer(
            db,
            user_id="user-p",
            hotel_id=hotel.id,
            initial_price=150.00,
            current_price=140.00,
        )

        assert float(offer.initial_price) == 150.00  # type: ignore[arg-type]
        assert float(offer.current_price) == 140.00  # type: ignore[arg-type]
    finally:
        _close(db)


def test_tracked_offers_are_isolated_per_user() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)

        offer_a = create_tracked_offer(db, user_id="user-a1", hotel_id=hotel.id)
        offer_b = create_tracked_offer(db, user_id="user-b1", hotel_id=hotel.id)

        retrieved_a = get_tracked_offer_or_404(db, user_id="user-a1", tracked_offer_id=offer_a.id)
        assert retrieved_a.user_id == "user-a1"

        with pytest.raises(PermissionError):
            get_tracked_offer_or_404(db, user_id="user-a1", tracked_offer_id=offer_b.id)
    finally:
        _close(db)


# ── Snapshot tracking ──────────────────────────────────────────────


def test_snapshot_can_be_created_with_tracked_offer_id() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        offer = create_tracked_offer(db, user_id="user-s1", hotel_id=hotel.id)

        snapshot = HotelRateSnapshot(
            hotel_id=hotel.id,
            tracked_offer_id=offer.id,
            provider="mock",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=120.00,
            availability_status="available",
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        assert snapshot.tracked_offer_id == offer.id
        assert snapshot.availability_status == "available"
        assert snapshot.deep_link is None
        assert snapshot.provider_run_id is None
    finally:
        _close(db)


def test_snapshot_can_be_created_without_tracked_offer_id() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)

        snapshot = HotelRateSnapshot(
            hotel_id=hotel.id,
            provider="mock",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=120.00,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        assert snapshot.tracked_offer_id is None
        assert snapshot.availability_status == "available"
    finally:
        _close(db)


def test_snapshot_can_be_associated_with_provider_run() -> None:
    db = _db()
    try:
        from app.infrastructure.db.models import HotelProviderRun

        hotel = _create_hotel(db)
        offer = create_tracked_offer(db, user_id="user-s2", hotel_id=hotel.id)

        provider_run = HotelProviderRun(provider="mock", status="completed")
        db.add(provider_run)
        db.flush()

        snapshot = HotelRateSnapshot(
            hotel_id=hotel.id,
            tracked_offer_id=offer.id,
            provider_run_id=provider_run.id,
            provider="mock",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=120.00,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        assert snapshot.provider_run_id == provider_run.id
        assert snapshot.tracked_offer_id == offer.id
    finally:
        _close(db)


def test_list_tracked_offer_snapshots_returns_only_own_snapshots() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        offer_a = create_tracked_offer(db, user_id="user-s3", hotel_id=hotel.id)
        offer_b = create_tracked_offer(db, user_id="user-s3", hotel_id=hotel.id)

        snap_a = HotelRateSnapshot(
            hotel_id=hotel.id,
            tracked_offer_id=offer_a.id,
            provider="mock",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=100.00,
        )
        snap_b1 = HotelRateSnapshot(
            hotel_id=hotel.id,
            tracked_offer_id=offer_b.id,
            provider="mock",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=200.00,
        )
        snap_b2 = HotelRateSnapshot(
            hotel_id=hotel.id,
            tracked_offer_id=offer_b.id,
            provider="booking",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=210.00,
        )
        # Unlinked snapshot (no tracked_offer_id)
        snap_unlinked = HotelRateSnapshot(
            hotel_id=hotel.id,
            provider="mock",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=300.00,
        )
        db.add_all([snap_a, snap_b1, snap_b2, snap_unlinked])
        db.commit()

        results_a = list_tracked_offer_snapshots(db, user_id="user-s3", tracked_offer_id=offer_a.id)
        results_b = list_tracked_offer_snapshots(db, user_id="user-s3", tracked_offer_id=offer_b.id)

        assert len(results_a) == 1
        assert results_a[0].amount == 100.00
        assert len(results_b) == 2
    finally:
        _close(db)


def test_list_tracked_offer_snapshots_empty_for_offer_with_no_snapshots() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        offer = create_tracked_offer(db, user_id="user-s4", hotel_id=hotel.id)

        results = list_tracked_offer_snapshots(db, user_id="user-s4", tracked_offer_id=offer.id)
        assert results == []
    finally:
        _close(db)


def test_list_tracked_offer_snapshots_enforces_ownership() -> None:
    db = _db()
    try:
        hotel = _create_hotel(db)
        offer = create_tracked_offer(db, user_id="user-s5", hotel_id=hotel.id)

        with pytest.raises(PermissionError, match="not_allowed"):
            list_tracked_offer_snapshots(db, user_id="user-other", tracked_offer_id=offer.id)
    finally:
        _close(db)


def test_snapshot_stores_availability_and_deep_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_HOSTS", "booking.com")
    monkeypatch.setenv("HOTEL_DEEPLINK_ALLOWED_QUERY_KEYS", "")
    db = _db()
    try:
        hotel = _create_hotel(db)
        offer = create_tracked_offer(db, user_id="user-s6", hotel_id=hotel.id)

        snapshot = HotelRateSnapshot(
            hotel_id=hotel.id,
            tracked_offer_id=offer.id,
            provider="booking",
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 3),
            guests=2,
            currency="EUR",
            amount=150.00,
            availability_status="unavailable",
            deep_link="https://booking.com/hotel/123",
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        assert snapshot.availability_status == "unavailable"
        assert snapshot.deep_link == "https://booking.com/hotel/123"
    finally:
        _close(db)
