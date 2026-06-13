"""Unit tests for Phase 8: sweep_tracked_offers — daily review of active tracked offers."""

from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelAlertEvent,
    HotelProperty,
    HotelProviderRun,
    HotelRateSnapshot,
    User,
)
from app.services.hotels_service import (
    create_tracked_offer,
    sweep_tracked_offers,
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


def _create_hotel(db: Session, *, name: str = "Hotel Test", city: str = "Madrid") -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=name,
        normalized_name=name.lower(),
        city=city,
        normalized_city=city.lower(),
        country_code="ES",
        stars=4,
        latitude=40.4168,
        longitude=-3.7038,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def _add_rate(
    db: Session,
    *,
    hotel_id: str,
    check_in: date,
    check_out: date,
    guests: int = 2,
    currency: str = "EUR",
    amount: float = 100.00,
    provider: str = "mock",
) -> HotelRateSnapshot:
    snapshot = HotelRateSnapshot(
        hotel_id=hotel_id,
        provider=provider,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        currency=currency,
        amount=amount,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _add_provider_run(db: Session, *, provider: str = "mock") -> HotelProviderRun:
    run = HotelProviderRun(provider=provider, status="completed")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


# ── Tests ──────────────────────────────────────────────────────

class TestSweepTrackedOffers:
    def test_creates_snapshots_for_active_tracked_offer_with_dates(self):
        """Active tracked offer with dates gets a snapshot from matching rates."""
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
                initial_price=100.00,
                currency="EUR",
            )

            # Add a matching unlinked rate (simulating a general sweep result)
            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=95.00,
            )

            provider_run = _add_provider_run(db)

            result = sweep_tracked_offers(db, provider_run_id=provider_run.id)
            assert result["offers_scanned"] == 1
            assert result["snapshots_created"] == 1

            # Verify snapshot was created and linked
            snapshots = db.scalars(
                select(HotelRateSnapshot).where(
                    HotelRateSnapshot.tracked_offer_id == offer.id,
                )
            ).all()
            assert len(snapshots) == 2  # initial + sweep snapshot
            sweep_snap = [s for s in snapshots if s.provider_run_id == provider_run.id]
            assert len(sweep_snap) == 1
            assert float(sweep_snap[0].amount) == 95.00

            # Verify current_price was updated
            db.refresh(offer)
            assert float(offer.current_price) == 95.00  # type: ignore[arg-type]
        finally:
            _close(db)

    def test_creates_alert_event_when_price_changes(self):
        """When sweep detects a different price, an alert event is created."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            _offer = create_tracked_offer(
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

            # Add a rate with different price
            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=80.00,
            )

            provider_run = _add_provider_run(db)

            sweep_tracked_offers(db, provider_run_id=provider_run.id)

            # Check for alert events
            events = db.scalars(select(HotelAlertEvent)).all()
            assert len(events) == 1
            assert events[0].hotel_id == hotel.id
            assert events[0].provider_run_id == provider_run.id
            assert events[0].event_type == "price_below"
            assert "bajó" in events[0].message
            assert "100.00" in events[0].message
            assert "80.00" in events[0].message
        finally:
            _close(db)

    def test_no_alert_when_price_is_same(self):
        """When sweep finds the same price, no alert event is created."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            _offer = create_tracked_offer(
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

            # Add a rate with the same price as initial
            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=100.00,
            )

            provider_run = _add_provider_run(db)

            sweep_tracked_offers(db, provider_run_id=provider_run.id)

            # No alert events (price didn't change from previous snapshot)
            events = db.scalars(select(HotelAlertEvent)).all()
            # The previous snapshot was created at offer creation with amount=100.00
            # The sweep found 100.00, same price → no event
            assert len(events) == 0
        finally:
            _close(db)

    def test_skips_tracked_offer_without_dates(self):
        """Tracked offers without check_in/check_out are skipped."""
        db = _db()
        try:
            user = _create_user(db)
            hotel = _create_hotel(db)

            # Create offer without dates
            offer = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel.id,
                provider="mock",
                currency="EUR",
            )

            provider_run = _add_provider_run(db)

            result = sweep_tracked_offers(db, provider_run_id=provider_run.id)
            assert result["offers_scanned"] == 0
            assert result["snapshots_created"] == 0

            # No new snapshots
            snapshots = db.scalars(
                select(HotelRateSnapshot).where(
                    HotelRateSnapshot.tracked_offer_id == offer.id,
                )
            ).all()
            assert len(snapshots) == 0
        finally:
            _close(db)

    def test_skips_inactive_tracked_offer(self):
        """Inactive tracked offers are not scanned."""
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
                initial_price=100.00,
                currency="EUR",
            )

            # Deactivate the offer
            offer.is_active = False
            db.add(offer)
            db.commit()

            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=90.00,
            )

            provider_run = _add_provider_run(db)

            result = sweep_tracked_offers(db, provider_run_id=provider_run.id)
            assert result["offers_scanned"] == 0
            assert result["snapshots_created"] == 0
        finally:
            _close(db)

    def test_handles_multiple_tracked_offers(self):
        """Can sweep multiple active tracked offers in one run."""
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
                initial_price=100.00,
                currency="EUR",
            )

            # Create a second hotel and tracked offer
            hotel2 = _create_hotel(db, name="Hotel Dos", city="Barcelona")
            offer2 = create_tracked_offer(
                db,
                user_id=user.id,
                hotel_id=hotel2.id,
                check_in=date(2026, 9, 1),
                check_out=date(2026, 9, 3),
                guests=3,
                provider="booking",
                initial_price=200.00,
                currency="EUR",
            )

            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=95.00,
            )
            _add_rate(
                db,
                hotel_id=hotel2.id,
                check_in=date(2026, 9, 1),
                check_out=date(2026, 9, 3),
                guests=3,
                currency="EUR",
                amount=180.00,
            )

            provider_run = _add_provider_run(db)

            result = sweep_tracked_offers(db, provider_run_id=provider_run.id)
            assert result["offers_scanned"] == 2
            assert result["snapshots_created"] == 2

            db.refresh(offer1)
            db.refresh(offer2)
            assert float(offer1.current_price) == 95.00  # type: ignore[arg-type]
            assert float(offer2.current_price) == 180.00  # type: ignore[arg-type]
        finally:
            _close(db)

    def test_no_matching_rate_does_not_create_snapshot(self):
        """If no matching rate exists in the pool, no snapshot is created."""
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
                initial_price=100.00,
                currency="EUR",
            )

            # No matching rate added
            provider_run = _add_provider_run(db)

            result = sweep_tracked_offers(db, provider_run_id=provider_run.id)
            assert result["offers_scanned"] == 1
            assert result["snapshots_created"] == 0

            # current_price unchanged
            db.refresh(offer)
            assert float(offer.current_price) == 100.00  # type: ignore[arg-type]
        finally:
            _close(db)

    def test_second_sweep_detects_price_change(self):
        """Two consecutive sweeps: second sweep creates alert if price changes from first."""
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
                initial_price=100.00,
                currency="EUR",
            )

            # First sweep with price 95
            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=95.00,
            )
            provider_run1 = _add_provider_run(db)
            sweep_tracked_offers(db, provider_run_id=provider_run1.id)

            db.refresh(offer)
            assert float(offer.current_price) == 95.00  # type: ignore[arg-type]

            # Second sweep with price 85 (changed)
            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=85.00,
            )
            provider_run2 = _add_provider_run(db, provider="mock")
            sweep_tracked_offers(db, provider_run_id=provider_run2.id)

            db.refresh(offer)
            assert float(offer.current_price) == 85.00  # type: ignore[arg-type]

            # An alert event should exist from the second sweep (price dropped)
            events = db.scalars(
                select(HotelAlertEvent).where(
                    HotelAlertEvent.provider_run_id == provider_run2.id,
                )
            ).all()
            assert len(events) == 1
            assert events[0].event_type == "price_below"
            assert "95.00" in events[0].message
            assert "85.00" in events[0].message
        finally:
            _close(db)


class TestRunHotelSweepIncludesTrackedOffers:
    """Full run_hotel_sweep integration tested in test_hotels_api_flow.py.

    Here we verify sweep_tracked_offers is idempotent and works after
    the full sweep pattern (ingest + sweep tracked).
    """

    def test_sweep_tracked_offers_idempotent(self):
        """Running sweep_tracked_offers twice with same data produces one snapshot per sweep."""
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
                initial_price=110.00,
                currency="EUR",
            )

            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=110.00,
            )

            provider_run1 = _add_provider_run(db)
            result1 = sweep_tracked_offers(db, provider_run_id=provider_run1.id)
            assert result1["snapshots_created"] == 1

            # Add another unlinked rate (simulating a new sweep ingestion)
            _add_rate(
                db,
                hotel_id=hotel.id,
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 3),
                guests=2,
                currency="EUR",
                amount=105.00,
            )

            provider_run2 = _add_provider_run(db, provider="mock")
            result2 = sweep_tracked_offers(db, provider_run_id=provider_run2.id)
            assert result2["snapshots_created"] == 1

            # Two sweep snapshots + initial snapshot = 3 total
            snapshots = db.scalars(
                select(HotelRateSnapshot).where(
                    HotelRateSnapshot.tracked_offer_id == offer.id,
                )
            ).all()
            assert len(snapshots) == 3

            db.refresh(offer)
            assert float(offer.current_price) == 105.00  # type: ignore[arg-type]
        finally:
            _close(db)
