from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.db.models import (
    HotelProviderAlias,
    HotelRateSnapshot,
    HotelStayOffer,
    HotelUserStayWatch,
)
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _open_overridden_db():
    generator = app.dependency_overrides[get_db]()
    return next(generator), generator


def _close_overridden_db(generator) -> None:
    try:
        next(generator)
    except StopIteration:
        pass


def test_tracked_offer_api_dual_writes_only_with_explicit_flags(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    monkeypatch.setenv("HOTEL_CANONICAL_MODEL_ENABLED", "true")
    monkeypatch.setenv("HOTEL_CANONICAL_DUAL_WRITE_ENABLED", "true")
    token = register_and_token(client, email="canonical-api@viru.dev")
    headers = _auth(token)

    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]
    db, generator = _open_overridden_db()
    try:
        db.add(
            HotelProviderAlias(
                hotel_id=hotel_id,
                provider="mock",
                provider_hotel_id="mock-api-canonical-001",
                confidence_score=1,
            )
        )
        db.commit()
    finally:
        _close_overridden_db(generator)
    response = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers,
        json={
            "hotel_id": hotel_id,
            "check_in": "2026-09-10",
            "check_out": "2026-09-13",
            "guests": 2,
            "provider": "mock",
            "initial_price": 180,
            "currency": "EUR",
        },
    )

    assert response.status_code == 201
    tracked_offer_id = response.json()["id"]
    db, generator = _open_overridden_db()
    try:
        watch = db.scalar(
            select(HotelUserStayWatch).where(
                HotelUserStayWatch.legacy_tracked_offer_id == tracked_offer_id
            )
        )
        stay_offer = db.get(HotelStayOffer, watch.stay_offer_id) if watch is not None else None
        snapshot = db.scalar(
            select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == tracked_offer_id)
        )

        assert stay_offer is not None
        assert watch is not None
        assert snapshot is not None
        assert watch.stay_offer_id == stay_offer.id
        assert watch.legacy_tracked_offer_id == tracked_offer_id
        assert snapshot.stay_offer_id == stay_offer.id
    finally:
        _close_overridden_db(generator)
