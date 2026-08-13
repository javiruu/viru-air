from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, HotelSavedSearch, User
from app.services import hotels_service


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


def _create_user(db: Session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_saved_hotel_search_is_idempotent_and_canonicalizes_query() -> None:
    db = _db()
    try:
        user = _create_user(db, "saved-a@example.com")
        query_a = {"schema": "hotel-search-v1", "params": {"q": "Royal"}}
        query_b = {"params": {"guests": "2", "q": "Royal", "radius": "10", "mode": "name"}, "schema": "hotel-search-v1"}

        first = hotels_service.create_saved_hotel_search(
            db, user_id=user.id, schema_version="hotel-search-v1", query=query_a, label="Madrid"
        )
        second = hotels_service.create_saved_hotel_search(
            db, user_id=user.id, schema_version="hotel-search-v1", query=query_b, label="Renombrada"
        )

        assert first.id == second.id
        assert second.label == "Madrid"
        assert db.query(HotelSavedSearch).count() == 1
    finally:
        _close(db)


def test_saved_hotel_search_rejects_direct_call_overrides() -> None:
    db = _db()
    try:
        user = _create_user(db, "saved-validation@example.com")
        with pytest.raises(ValueError, match="invalid_saved_search_query"):
            hotels_service.create_saved_hotel_search(
                db,
                user_id=user.id,
                schema_version="hotel-search-v1",
                query={
                    "schema": "hotel-search-v1",
                    "params": {"q": "x" * 121},
                },
                label=None,
            )
        with pytest.raises(ValueError, match="invalid_saved_search_query"):
            hotels_service.create_saved_hotel_search(
                db,
                user_id=user.id,
                schema_version="hotel-search-v1",
                query={
                    "schema": "hotel-search-v1",
                    "params": {"mode": "area", "area": "Madrid", "area_lat": "40.4168", "area_lng": "-3.7038", "area_country": "ESP", "check_in": "2026-09-12", "check_out": "2026-09-15"},
                },
                label=None,
            )
        with pytest.raises(ValueError, match="invalid_saved_search_label"):
            hotels_service.create_saved_hotel_search(
                db,
                user_id=user.id,
                schema_version="hotel-search-v1",
                query={"schema": "hotel-search-v1", "params": {"q": "Royal"}},
                label="x" * 121,
            )
    finally:
        _close(db)


def test_saved_hotel_search_enforces_ownership() -> None:
    db = _db()
    try:
        owner = _create_user(db, "saved-owner@example.com")
        foreign = _create_user(db, "saved-foreign@example.com")
        row = hotels_service.create_saved_hotel_search(
            db,
            user_id=owner.id,
            schema_version="hotel-search-v1",
            query={"schema": "hotel-search-v1", "params": {"q": "Royal"}},
            label=None,
        )

        try:
            hotels_service.get_saved_hotel_search_or_404(db, user_id=foreign.id, saved_search_id=row.id)
        except PermissionError as exc:
            assert str(exc) == "not_allowed"
        else:
            raise AssertionError("foreign saved search must be forbidden")
    finally:
        _close(db)


def test_saved_hotel_search_update_and_delete() -> None:
    db = _db()
    try:
        user = _create_user(db, "saved-update@example.com")
        row = hotels_service.create_saved_hotel_search(
            db,
            user_id=user.id,
            schema_version="hotel-search-v1",
            query={"schema": "hotel-search-v1", "params": {"mode": "area", "area": "Madrid", "area_lat": "40.4168", "area_lng": "-3.7038", "area_country": "ES", "check_in": "2026-09-12", "check_out": "2026-09-15"}},
            label="Inicial",
        )

        updated = hotels_service.update_saved_hotel_search(
            db,
            user_id=user.id,
            saved_search_id=row.id,
            update_data={"label": "Pausada", "status": "paused"},
        )
        assert updated.label == "Pausada"
        assert updated.status == "paused"

        hotels_service.delete_saved_hotel_search(db, user_id=user.id, saved_search_id=row.id)
        assert db.get(HotelSavedSearch, row.id) is None
    finally:
        _close(db)
