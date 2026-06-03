from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelAlertRule,
    HotelCompSet,
    HotelCompSetMember,
    HotelProperty,
    HotelProviderAlias,
    HotelRateSnapshot,
    HotelWatchlistItem,
    User,
)


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_user(db: Session, email: str = "hotels-models@viru.dev") -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_hotel(db: Session, canonical_name: str, normalized_name: str) -> HotelProperty:
    hotel = HotelProperty(
        canonical_name=canonical_name,
        normalized_name=normalized_name,
        city="Madrid",
        country_code="ES",
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def test_hotel_provider_alias_unique_per_provider_hotel_id(db: Session) -> None:
    hotel = _seed_hotel(db, "Hotel Sol", "hotel sol")
    first = HotelProviderAlias(
        hotel_id=hotel.id,
        provider="mock",
        provider_hotel_id="mock-001",
    )
    db.add(first)
    db.commit()

    duplicate = HotelProviderAlias(
        hotel_id=hotel.id,
        provider="mock",
        provider_hotel_id="mock-001",
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_hotel_watchlist_item_unique_per_user_and_hotel(db: Session) -> None:
    user = _seed_user(db)
    hotel = _seed_hotel(db, "Hotel Luna", "hotel luna")

    first = HotelWatchlistItem(user_id=user.id, hotel_id=hotel.id)
    db.add(first)
    db.commit()

    duplicate = HotelWatchlistItem(user_id=user.id, hotel_id=hotel.id)
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_hotel_comp_set_member_unique_per_comp_set_and_hotel(db: Session) -> None:
    user = _seed_user(db, email="comp-set@viru.dev")
    anchor = _seed_hotel(db, "Hotel Brisa", "hotel brisa")
    member_hotel = _seed_hotel(db, "Hotel Costa", "hotel costa")

    comp_set = HotelCompSet(user_id=user.id, name="Costa set", anchor_hotel_id=anchor.id)
    db.add(comp_set)
    db.commit()
    db.refresh(comp_set)

    first = HotelCompSetMember(comp_set_id=comp_set.id, hotel_id=member_hotel.id)
    db.add(first)
    db.commit()

    duplicate = HotelCompSetMember(comp_set_id=comp_set.id, hotel_id=member_hotel.id)
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_hotel_rate_snapshot_persists_phase1_fields(db: Session) -> None:
    hotel = _seed_hotel(db, "Hotel Prisma", "hotel prisma")

    snapshot = HotelRateSnapshot(
        hotel_id=hotel.id,
        provider="mock",
        check_in=date(2026, 7, 10),
        check_out=date(2026, 7, 12),
        guests=2,
        room_label="Deluxe",
        meal_plan="breakfast",
        cancellation_policy="flexible",
        currency="EUR",
        amount=189.50,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    persisted = db.get(HotelRateSnapshot, snapshot.id)
    assert persisted is not None
    assert persisted.hotel_id == hotel.id
    assert persisted.provider == "mock"
    assert float(persisted.amount) == pytest.approx(189.50)
    assert persisted.currency == "EUR"


def test_hotel_provider_alias_can_store_internal_raw_payload(db: Session) -> None:
    hotel = _seed_hotel(db, "Hotel Faro", "hotel faro")

    alias = HotelProviderAlias(
        hotel_id=hotel.id,
        provider="mock",
        provider_hotel_id="mock-faro-001",
        raw_name="Hotel Faro Madrid",
        raw_address="Calle Radar 7",
        raw_payload='{"source":"mock","hotel_code":"faro-001"}',
        confidence_score=98.5,
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)

    persisted = db.get(HotelProviderAlias, alias.id)
    assert persisted is not None
    assert persisted.raw_payload == '{"source":"mock","hotel_code":"faro-001"}'
    assert float(persisted.confidence_score) == pytest.approx(98.5)


def test_hotel_alert_rule_persists_user_owned_thresholds(db: Session) -> None:
    user = _seed_user(db, email="alerts-phase1@viru.dev")
    hotel = _seed_hotel(db, "Hotel Umbral", "hotel umbral")

    rule = HotelAlertRule(
        user_id=user.id,
        hotel_id=hotel.id,
        rule_type="price_below",
        threshold_amount=150,
        threshold_percent=8,
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    persisted = db.get(HotelAlertRule, rule.id)
    assert persisted is not None
    assert persisted.user_id == user.id
    assert persisted.hotel_id == hotel.id
    assert persisted.rule_type == "price_below"
    assert float(persisted.threshold_amount) == pytest.approx(150)
    assert float(persisted.threshold_percent) == pytest.approx(8)
    assert persisted.is_active is True
