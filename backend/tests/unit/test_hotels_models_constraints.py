import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import (
    Base,
    HotelCompSet,
    HotelCompSetMember,
    HotelProperty,
    HotelProviderAlias,
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
