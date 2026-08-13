from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime
from contextlib import suppress

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import HotelRateSnapshot, HotelStayOffer, HotelTrackedOffer
from app.infrastructure.db.session import get_db
from app.main import app

from tests.helpers import register_and_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _open_overridden_db() -> tuple[Session, Generator[Session, None, None]]:
    generator = app.dependency_overrides[get_db]()
    return next(generator), generator


def _close_overridden_db(generator: Generator[Session, None, None]) -> None:
    with suppress(StopIteration):
        next(generator)


def _create_offer(
    client: TestClient,
    *,
    headers: dict[str, str],
    hotel_id: str,
    payload: dict[str, str | float],
) -> str:
    response = client.post(
        "/api/v1/hotels/tracked-offers",
        headers=headers,
        json={"hotel_id": hotel_id, "provider": "mock", "currency": "EUR", **payload},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_tracked_offers_v2_classifies_legacy_context_without_claiming_active(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-tracking-v2@viru.dev")
    other_token = register_and_token(client, email="hotels-tracking-v2-other@viru.dev")
    headers = {**_auth(token), "x-correlation-id": "hotels-tracking-v2-001"}

    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]
    pending_context = _create_offer(client, headers=headers, hotel_id=hotel_id, payload={})
    legacy_snapshot = _create_offer(
        client,
        headers=headers,
        hotel_id=hotel_id,
        payload={
            "check_in": "2026-09-10",
            "check_out": "2026-09-13",
            "initial_price": 180,
        },
    )
    paused = _create_offer(
        client,
        headers=headers,
        hotel_id=hotel_id,
        payload={
            "check_in": "2026-09-20",
            "check_out": "2026-09-23",
            "initial_price": 200,
        },
    )
    assert client.patch(
        f"/api/v1/hotels/tracked-offers/{paused}",
        headers=headers,
        json={"is_active": False},
    ).status_code == 200

    response = client.get("/api/v1/hotels/v2/tracked-offers", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["contract_version"] == "hotels.tracking.v2"
    assert payload["meta"]["request_id"] == "hotels-tracking-v2-001"
    assert payload["meta"]["result_state"] == "partial"
    by_id = {item["id"]: item for item in payload["data"]}
    assert by_id[pending_context]["state"] == "pending_context"
    assert by_id[pending_context]["latest_observation"] is None
    assert by_id[legacy_snapshot]["state"] == "partial"
    assert by_id[legacy_snapshot]["latest_observation"]["price"]["basis"] == "unknown"
    assert {warning["code"] for warning in by_id[legacy_snapshot]["warnings"]} >= {
        "legacy_tracking_contract",
        "price_semantics_unknown",
    }
    assert by_id[legacy_snapshot]["capabilities"]["external_delivery"] == "unavailable"
    assert by_id[paused]["state"] == "paused"

    other_response = client.get("/api/v1/hotels/v2/tracked-offers", headers=_auth(other_token))
    assert other_response.status_code == 200
    assert other_response.json()["data"] == []


def test_tracked_offers_v2_creates_an_active_private_bridge_from_an_eligible_source_rate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-tracking-v2-create@viru.dev")
    headers = _auth(token)
    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    db, generator = _open_overridden_db()
    try:
        stay_offer = HotelStayOffer(
            canonical_hotel_id=hotel_id,
            provider="mock",
            provider_hotel_id="mock-v2-source-001",
            stay_query_fingerprint="a" * 64,
            offer_fingerprint="b" * 64,
            canonical_query_json="{}",
            conditions_completeness="complete",
            fee_semantics="total",
        )
        db.add(stay_offer)
        db.flush()
        source_rate = HotelRateSnapshot(
            hotel_id=hotel_id,
            stay_offer_id=stay_offer.id,
            provider="mock",
            check_in=date(2026, 10, 10),
            check_out=date(2026, 10, 13),
            guests=2,
            room_label="Doble superior",
            meal_plan="BB",
            cancellation_policy="Reembolsable",
            currency="EUR",
            amount=240,
            amount_total=240,
            availability_status="available",
            observed_at=datetime(2026, 8, 11, 12, 0, 0),
            stay_query_fingerprint=stay_offer.stay_query_fingerprint,
            offer_fingerprint=stay_offer.offer_fingerprint,
            snapshot_outcome="success",
            price_semantics="total",
            conditions_completeness="complete",
        )
        db.add(source_rate)
        db.commit()
        source_rate_id = source_rate.id
    finally:
        _close_overridden_db(generator)

    created = client.post("/api/v1/hotels/v2/tracked-offers", headers=headers, json={"source_rate_id": source_rate_id})

    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["creation"] == {"outcome": "created", "semantic_dedupe": False}
    assert payload["tracking"]["state"] == "active"
    assert payload["tracking"]["latest_observation"]["price"] == {
        "amount": 240.0,
        "currency": "EUR",
        "basis": "total_stay",
        "status": "observed",
        "observed_at": "2026-08-11T12:00:00",
    }
    observation = payload["tracking"]["latest_observation"]
    assert observation["provider"] == "mock"
    assert observation["room_label"] == "Doble superior"
    assert observation["meal_plan"] == "BB"
    assert observation["cancellation_policy"] == "Reembolsable"
    assert observation["availability_status"] == "available"
    assert observation["conditions_completeness"] == "complete"
    duplicate = client.post("/api/v1/hotels/v2/tracked-offers", headers=headers, json={"source_rate_id": source_rate_id})
    assert duplicate.status_code == 200
    assert duplicate.json()["creation"] == {"outcome": "existing", "semantic_dedupe": True}
    assert duplicate.json()["tracking"]["id"] == payload["tracking"]["id"]

    other_token = register_and_token(client, email="hotels-tracking-v2-create-other@viru.dev")
    other_created = client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=_auth(other_token),
        json={"source_rate_id": source_rate_id},
    )
    assert other_created.status_code == 201, other_created.text
    assert other_created.json()["tracking"]["id"] != payload["tracking"]["id"]
    foreign_private_source = client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=_auth(other_token),
        json={"source_rate_id": payload["tracking"]["latest_observation"]["snapshot_id"]},
    )
    assert foreign_private_source.status_code == 404
    assert foreign_private_source.json().get("code") == "hotel_source_rate_not_found"
    assert client.get(
        f"/api/v1/hotels/tracked-offers/{payload['tracking']['id']}/snapshots",
        headers=_auth(other_token),
    ).status_code == 403
    public_rates = client.get(f"/api/v1/hotels/{hotel_id}/rates", headers=_auth(other_token))
    assert public_rates.status_code == 200
    assert any(rate["id"] == source_rate_id for rate in public_rates.json())
    assert all(rate["tracked_offer_id"] is None for rate in public_rates.json())

    db, generator = _open_overridden_db()
    try:
        private_snapshots = list(
            db.scalars(
                select(HotelRateSnapshot).where(
                    HotelRateSnapshot.tracked_offer_id.in_(
                        [payload["tracking"]["id"], other_created.json()["tracking"]["id"]]
                    )
                )
            )
        )
        assert len(private_snapshots) == 2
        assert {snapshot.tracked_offer_id for snapshot in private_snapshots} == {
            payload["tracking"]["id"],
            other_created.json()["tracking"]["id"],
        }
        assert all(snapshot.id != source_rate_id and snapshot.amount_total == 240 for snapshot in private_snapshots)
        next(snapshot for snapshot in private_snapshots if snapshot.tracked_offer_id == payload["tracking"]["id"]).availability_status = "unavailable"
        db.commit()
    finally:
        _close_overridden_db(generator)

    unavailable = client.get("/api/v1/hotels/v2/tracked-offers", headers=headers)
    assert unavailable.status_code == 200
    unavailable_tracking = next(item for item in unavailable.json()["data"] if item["id"] == payload["tracking"]["id"])
    assert unavailable_tracking["state"] == "unavailable"
    assert unavailable_tracking["latest_observation"]["price"]["status"] == "unavailable"
    assert "observation_unavailable" in {warning["code"] for warning in unavailable_tracking["warnings"]}


def test_tracked_offers_v2_creates_an_active_private_bridge_from_an_eligible_mock_rate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-tracking-v2-ineligible@viru.dev")
    headers = _auth(token)
    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]
    source_rate = client.get(
        f"/api/v1/hotels/{hotel_id}/rates",
        headers=headers,
        params={"check_in": "2026-07-10", "check_out": "2026-07-12"},
    ).json()[0]
    source_rate_id = source_rate["id"]

    response = client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": source_rate_id},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["creation"] == {"outcome": "created", "semantic_dedupe": False}
    assert payload["tracking"]["state"] == "active"
    assert payload["tracking"]["latest_observation"]["price"] == {
        "amount": source_rate["amount"],
        "currency": source_rate["currency"],
        "basis": "total_stay",
        "status": "observed",
        "observed_at": payload["tracking"]["latest_observation"]["price"]["observed_at"],
    }
    assert payload["tracking"]["latest_observation"]["conditions_completeness"] == "complete"
    assert client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": "not-a-uuid"},
    ).status_code == 422
    assert client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": source_rate_id, "user_id": "forbidden"},
    ).status_code == 422
    assert client.get("/api/v1/hotels/v2/tracked-offers", headers=headers).json()["data"] == [payload["tracking"]]


def test_tracked_offers_v2_lifecycle_is_versioned_owned_and_idempotent(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-tracking-v2-lifecycle@viru.dev")
    headers = _auth(token)
    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]
    source_rate = client.get(
        f"/api/v1/hotels/{hotel_id}/rates",
        headers=headers,
        params={"check_in": "2026-07-10", "check_out": "2026-07-12"},
    ).json()[0]
    created = client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": source_rate["id"]},
    )
    assert created.status_code == 201, created.text
    tracking = created.json()["tracking"]
    db, generator = _open_overridden_db()
    try:
        offer = db.get(HotelTrackedOffer, tracking["id"])
        assert offer is not None
        offer.check_in = date(2026, 12, 10)
        offer.check_out = date(2026, 12, 12)
        db.commit()
    finally:
        _close_overridden_db(generator)

    paused = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=headers,
        json={"action": "pause", "expected_state_version": 1},
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["outcome"] == "applied"
    assert paused.json()["tracking"]["state"] == "paused"
    assert paused.json()["tracking"]["state_version"] == 2

    duplicate_pause = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=headers,
        json={"action": "pause", "expected_state_version": 2},
    )
    assert duplicate_pause.status_code == 200
    assert duplicate_pause.json()["outcome"] == "existing"
    assert duplicate_pause.json()["tracking"]["state_version"] == 2

    conflict = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=headers,
        json={"action": "resume", "expected_state_version": 1},
    )
    assert conflict.status_code == 409
    assert conflict.json().get("code") == "tracked_offer_state_conflict"

    other_token = register_and_token(client, email="hotels-tracking-v2-lifecycle-other@viru.dev")
    forbidden = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=_auth(other_token),
        json={"action": "resume", "expected_state_version": 2},
    )
    assert forbidden.status_code == 403

    resumed = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=headers,
        json={"action": "resume", "expected_state_version": 2},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["outcome"] == "applied"
    assert resumed.json()["tracking"]["state"] == "active"
    assert resumed.json()["tracking"]["state_version"] == 3

    archived = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=headers,
        json={"action": "archive", "expected_state_version": 3},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["outcome"] == "applied"
    assert archived.json()["tracking"]["state"] == "archived"
    assert archived.json()["tracking"]["state_version"] == 4

    duplicate_archive = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=headers,
        json={"action": "archive", "expected_state_version": 4},
    )
    assert duplicate_archive.status_code == 200
    assert duplicate_archive.json()["outcome"] == "existing"

    archived_cannot_resume = client.patch(
        f"/api/v1/hotels/v2/tracked-offers/{tracking['id']}/lifecycle",
        headers=headers,
        json={"action": "resume", "expected_state_version": 4},
    )
    assert archived_cannot_resume.status_code == 422


def test_tracked_offers_v2_rejects_a_legacy_source_rate_without_total_semantics(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-tracking-v2-legacy-source@viru.dev")
    headers = _auth(token)
    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    db, generator = _open_overridden_db()
    try:
        legacy_source = HotelRateSnapshot(
            hotel_id=hotel_id,
            provider="mock",
            check_in=date(2026, 11, 10),
            check_out=date(2026, 11, 12),
            guests=2,
            currency="EUR",
            amount=189.5,
            availability_status="available",
        )
        db.add(legacy_source)
        db.commit()
        source_rate_id = legacy_source.id
    finally:
        _close_overridden_db(generator)

    response = client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": source_rate_id},
    )

    assert response.status_code == 422
    assert response.json().get("code") == "hotel_source_rate_not_eligible"
    assert client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": "not-a-uuid"},
    ).status_code == 422
    assert client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": source_rate_id, "user_id": "forbidden"},
    ).status_code == 422
    assert client.get("/api/v1/hotels/v2/tracked-offers", headers=headers).json()["data"] == []


def test_tracked_offer_history_v2_keeps_private_canonical_points_and_honest_aggregates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-tracking-v2-history@viru.dev")
    other_token = register_and_token(client, email="hotels-tracking-v2-history-other@viru.dev")
    headers = _auth(token)
    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    hotel_id = client.get("/api/v1/hotels/search", headers=headers).json()[0]["id"]

    db, generator = _open_overridden_db()
    try:
        stay_offer = HotelStayOffer(
            canonical_hotel_id=hotel_id,
            provider="mock",
            provider_hotel_id="mock-v2-history-001",
            stay_query_fingerprint="c" * 64,
            offer_fingerprint="d" * 64,
            canonical_query_json="{}",
            conditions_completeness="complete",
            fee_semantics="total",
        )
        db.add(stay_offer)
        db.flush()
        source = HotelRateSnapshot(
            hotel_id=hotel_id,
            stay_offer_id=stay_offer.id,
            provider="mock",
            check_in=date(2026, 11, 10),
            check_out=date(2026, 11, 12),
            guests=2,
            currency="EUR",
            amount=240,
            amount_total=240,
            availability_status="available",
            observed_at=datetime(2026, 8, 10, 10, 0, 0),
            stay_query_fingerprint=stay_offer.stay_query_fingerprint,
            offer_fingerprint=stay_offer.offer_fingerprint,
            snapshot_outcome="success",
            price_semantics="total",
            conditions_completeness="complete",
        )
        db.add(source)
        db.commit()
        source_rate_id = source.id
    finally:
        _close_overridden_db(generator)

    created = client.post(
        "/api/v1/hotels/v2/tracked-offers",
        headers=headers,
        json={"source_rate_id": source_rate_id},
    )
    assert created.status_code == 201, created.text
    tracked_offer_id = created.json()["tracking"]["id"]

    db, generator = _open_overridden_db()
    try:
        existing = db.scalar(select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == tracked_offer_id))
        assert existing is not None
        db.add_all(
            [
                HotelRateSnapshot(
                    hotel_id=hotel_id,
                    stay_offer_id=existing.stay_offer_id,
                    tracked_offer_id=tracked_offer_id,
                    provider="mock",
                    check_in=existing.check_in,
                    check_out=existing.check_out,
                    guests=2,
                    currency="EUR",
                    amount=220,
                    amount_total=220,
                    availability_status="available",
                    observed_at=datetime(2026, 8, 11, 10, 0, 0),
                    stay_query_fingerprint=existing.stay_query_fingerprint,
                    offer_fingerprint=existing.offer_fingerprint,
                    snapshot_outcome="success",
                    price_semantics="total",
                    conditions_completeness="complete",
                ),
                HotelRateSnapshot(
                    hotel_id=hotel_id,
                    stay_offer_id=existing.stay_offer_id,
                    tracked_offer_id=tracked_offer_id,
                    provider="mock",
                    check_in=existing.check_in,
                    check_out=existing.check_out,
                    guests=2,
                    currency="EUR",
                    amount=200,
                    amount_total=200,
                    availability_status="available",
                    observed_at=datetime(2026, 8, 12, 10, 0, 0),
                    stay_query_fingerprint=existing.stay_query_fingerprint,
                    offer_fingerprint=existing.offer_fingerprint,
                    snapshot_outcome="success",
                    price_semantics="total",
                    conditions_completeness="complete",
                ),
            ]
        )
        db.commit()
    finally:
        _close_overridden_db(generator)

    response = client.get(f"/api/v1/hotels/v2/tracked-offers/{tracked_offer_id}/history", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["tracked_offer_id"] == tracked_offer_id
    assert payload["series"]["identity"]["status"] == "comparable"
    assert [point["price"]["amount"] for point in payload["series"]["points"]] == [240, 220, 200]
    assert all(point["eligibility"] == "eligible" for point in payload["series"]["points"])
    assert payload["aggregates"] == {
        "sample_size_total": 3,
        "sample_size_eligible": 3,
        "min_price": 200,
        "max_price": 240,
        "median_price": 220,
        "average_price": 220,
        "currency": "EUR",
        "price_semantics": "total",
        "exclusions": {},
    }
    window = client.get(
        f"/api/v1/hotels/v2/tracked-offers/{tracked_offer_id}/history?from=2026-08-11&to=2026-08-12",
        headers=headers,
    )
    assert window.status_code == 200
    assert [point["price"]["amount"] for point in window.json()["series"]["points"]] == [220, 200]
    assert client.get(
        f"/api/v1/hotels/v2/tracked-offers/{tracked_offer_id}/history",
        headers=_auth(other_token),
    ).status_code == 403
    assert client.get(
        f"/api/v1/hotels/v2/tracked-offers/{tracked_offer_id}/history?from=2026-08-13&to=2026-08-12",
        headers=headers,
    ).status_code == 422
