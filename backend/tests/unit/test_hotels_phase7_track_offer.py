"""Unit tests for HotelTrackedOffer snapshot creation and duplicate prevention (Phase 7)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelProperty,
    HotelRateSnapshot,
    HotelTrackedOffer,
    User,
)
from app.services.hotels_service import (
    create_tracked_offer,
    delete_tracked_offer,
    list_tracked_offers,
    list_tracked_offer_snapshots,
)


# ── Helpers ────────────────────────────────────────────────────

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


def _create_user(db: Session, *, email: str = "test@example.com") -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_hotel(db: Session, *, name: str = "Hotel Test") -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=name,
        normalized_name=name.lower(),
        city="Madrid",
        normalized_city="madrid",
        country_code="ES",
        stars=4,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


# ── Snapshot creation on create_tracked_offer ─────────────────

class TestCreateTrackedOfferWithSnapshot:
    """When creating a tracked offer with dates and price, an initial snapshot is created."""

    def test_creates_initial_snapshot_when_dates_and_price_provided(self):
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 7, 10),
                check_out=date(2026, 7, 12),
                guests=2,
                provider="mock",
                initial_price=150.00,
                currency="EUR",
            )
            assert offer.hotel_id == hotel.id
            assert offer.initial_price == 150.00

            snapshots = db.scalars(
                select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id)
            ).all()
            assert len(snapshots) == 1
            snap = snapshots[0]
            assert snap.hotel_id == hotel.id
            assert snap.tracked_offer_id == offer.id
            assert snap.provider == "mock"
            assert snap.check_in == date(2026, 7, 10)
            assert snap.check_out == date(2026, 7, 12)
            assert snap.guests == 2
            assert snap.currency == "EUR"
            assert float(snap.amount) == 150.00
            assert snap.availability_status == "available"
        finally:
            _close(db)

    def test_no_snapshot_when_dates_missing(self):
        """If dates are not provided, no initial snapshot is created."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                provider="mock",
                currency="EUR",
            )
            snapshots = db.scalars(
                select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id)
            ).all()
            assert len(snapshots) == 0
        finally:
            _close(db)

    def test_no_snapshot_when_price_missing(self):
        """If dates are provided but no price, no snapshot is created."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 7, 10),
                check_out=date(2026, 7, 12),
                guests=2,
                provider="mock",
                currency="EUR",
            )
            snapshots = db.scalars(
                select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id)
            ).all()
            assert len(snapshots) == 0
        finally:
            _close(db)

    def test_current_price_uses_initial_price_as_fallback(self):
        """When initial_price is set and current_price is not, current defaults to initial."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 7, 10),
                check_out=date(2026, 7, 12),
                initial_price=200.00,
                provider="mock",
                currency="EUR",
            )
            assert offer.current_price == 200.00
            assert offer.initial_price == 200.00
        finally:
            _close(db)


# ── Duplicate prevention ──────────────────────────────────────

class TestTrackedOfferDuplicatePrevention:
    """Creating the same tracked offer twice should raise a 409 error."""

    def test_duplicate_exact_match_raises_error(self):
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                provider="mock",
                initial_price=100.00,
                currency="EUR",
            )

            with pytest.raises(ValueError, match="tracked_offer_already_exists"):
                create_tracked_offer(
                    db,
                    user_id=user.id,
                    hotel_id=hotel.id,
                    check_in=date(2026, 8, 1),
                    check_out=date(2026, 8, 3),
                    guests=2,
                    provider="mock",
                    initial_price=100.00,
                    currency="EUR",
                )
        finally:
            _close(db)

    def test_different_dates_allowed(self):
        """Same hotel + user but different dates is allowed."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer1 = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                provider="mock",
            )
            offer2 = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 9, 1),
                check_out=date(2026, 9, 3),
                guests=2,
                provider="mock",
            )
            assert offer1.id != offer2.id
        finally:
            _close(db)

    def test_different_provider_allowed(self):
        """Same hotel + user + dates but different provider is allowed."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                provider="mock",
            )
            offer2 = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                provider="makcorps",
            )
            assert offer2 is not None
        finally:
            _close(db)

    def test_different_guests_allowed(self):
        """Same hotel + dates + provider but different guests is allowed."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer1 = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                provider="mock",
            )
            offer2 = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=4,
                provider="mock",
            )
            assert offer1.id != offer2.id
        finally:
            _close(db)

    def test_different_user_allowed(self):
        """Same hotel + dates but different user is allowed."""
        db = _db()
        try:
            user_a = _create_user(db, email="a@test.com")
            user_b = _create_user(db, email="b@test.com")
            hotel = _create_hotel(db)

            create_tracked_offer(
                db,
                user_id=user_a.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                provider="mock",
            )
            offer_b = create_tracked_offer(
                db,
                user_id=user_b.id,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                provider="mock",
            )
            assert offer_b is not None
        finally:
            _close(db)


# ── Snapshots after duplicate ─────────────────────────────────

class TestTrackedOfferSnapshotsAfterDuplicate:
    """Snapshots from the first creation are not duplicated on conflict."""

    def test_duplicate_does_not_create_extra_snapshot(self):
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 10, 1),
                check_out=date(2026, 10, 4),
                guests=2,
                provider="mock",
                initial_price=180.00,
                currency="EUR",
            )

            # Count snapshots for this hotel
            snapshots_before = db.scalars(
                select(HotelRateSnapshot).where(HotelRateSnapshot.hotel_id == hotel.id)
            ).all()
            count_before = len(snapshots_before)

            with pytest.raises(ValueError, match="tracked_offer_already_exists"):
                create_tracked_offer(
                    db,
                    user_id=user.id,
                    hotel_id=hotel.id,
                    check_in=date(2026, 10, 1),
                    check_out=date(2026, 10, 4),
                    guests=2,
                    provider="mock",
                    initial_price=200.00,
                    currency="EUR",
                )

            snapshots_after = db.scalars(
                select(HotelRateSnapshot).where(HotelRateSnapshot.hotel_id == hotel.id)
            ).all()
            assert len(snapshots_after) == count_before  # no new snapshots on rollback
        finally:
            _close(db)

    def test_list_snapshots_returns_only_linked(self):
        """list_tracked_offer_snapshots returns only snapshots for the given offer."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 11, 1),
                check_out=date(2026, 11, 3),
                guests=3,
                provider="mock",
                initial_price=120.00,
                currency="EUR",
            )

            # Create another offer for the same hotel (different dates = allowed)
            offer2 = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 12, 1),
                check_out=date(2026, 12, 3),
                guests=3,
                provider="mock",
                initial_price=140.00,
                currency="EUR",
            )

            # Snapshots for offer1 should not include offer2's snapshots
            snaps1 = list_tracked_offer_snapshots(db, user_id=user.id, tracked_offer_id=offer.id)
            assert len(snaps1) == 1
            assert snaps1[0].tracked_offer_id == offer.id

            snaps2 = list_tracked_offer_snapshots(db, user_id=user.id, tracked_offer_id=offer2.id)
            assert len(snaps2) == 1
            assert snaps2[0].tracked_offer_id == offer2.id
        finally:
            _close(db)


# ── Delete behaviour ──────────────────────────────────────────

class TestDeleteTrackedOffer:
    def test_delete_leaves_snapshots_intact(self):
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            offer = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                check_in=date(2026, 9, 1),
                check_out=date(2026, 9, 2),
                guests=1,
                provider="mock",
                initial_price=90.00,
                currency="EUR",
            )

            snapshot_count = db.scalars(
                select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id)
            ).all()
            assert len(snapshot_count) == 1

            delete_tracked_offer(db, user_id=user.id, tracked_offer_id=offer.id)

            # Offer should be gone
            offers = list_tracked_offers(db, user_id=user.id)
            assert len(offers) == 0

            # Snapshots should remain (tracked_offer_id becomes orphaned, which is fine)
            remaining = db.scalars(
                select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id)
            ).all()
            assert len(remaining) == 1  # snapshot survives delete (FK is nullable, no cascade)
        finally:
            _close(db)
