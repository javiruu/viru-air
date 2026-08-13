from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db.models import HotelProviderAlias, HotelProperty
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_area_search_v2_envelope_preserves_price_limits_and_request_context(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-results-v2@viru.dev")
    headers = {**_auth(token), "x-correlation-id": "hotels-v2-area-001"}

    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200
    response = client.get(
        "/api/v1/hotels/v2/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_km": 50,
            "check_in": "2026-07-10",
            "check_out": "2026-07-12",
            "guests": 2,
            "currency": "EUR",
            "sort": "price",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["contract_version"] == "hotels.results.v2"
    assert payload["meta"]["request_id"] == "hotels-v2-area-001"
    assert payload["meta"]["result_state"] == "success"
    assert payload["meta"]["pagination"] == {
        "mode": "none",
        "returned": len(payload["data"]),
        "total": len(payload["data"]),
        "has_next": False,
        "next_cursor": None,
        "previous_cursor": None,
        "sort": "price",
    }
    assert payload["meta"]["query"] == {
        "mode": "area",
        "check_in": "2026-07-10",
        "check_out": "2026-07-12",
        "guests": 2,
        "currency": "EUR",
        "radius_km": 50,
        "filters": {"min_stars": None, "max_price": None},
        "sort": "price",
    }
    assert payload["data"]
    price = payload["data"][0]["price"]
    assert price["amount"] == 189.5
    assert price["currency"] == "EUR"
    assert price["basis"] == "total_stay"
    assert price["status"] == "observed"
    assert price["observed_at"] is not None
    assert payload["data"][0]["stay_context"]["rooms"] is None
    assert payload["data"][0]["explanation"]["primary_reason"] == "lowest_observed_price"


def test_area_search_v2_exposes_disabled_provider_as_partial_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-results-v2-provider@viru.dev")
    headers = _auth(token)
    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200

    monkeypatch.setenv("HOTEL_PROFILE", "prod_off")
    response = client.get(
        "/api/v1/hotels/v2/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_km": 50,
            "check_in": "2026-07-10",
            "check_out": "2026-07-12",
            "use_provider": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["result_state"] == "partial"
    assert payload["meta"]["providers"] == [
        {
            "id": "mock",
            "operation": "area_search",
            "status": "disabled",
            "results_count": 0,
            "used_for_results": False,
            "fallback_used": False,
            "latency_ms": None,
        }
    ]
    assert payload["meta"]["warnings"][0]["code"] == "provider_unavailable"
    assert payload["data"]


def test_area_search_v2_exposes_runtime_provider_failure_with_cached_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTEL_PROFILE", "local_demo")
    monkeypatch.setenv("HOTEL_FEATURE_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")
    token = register_and_token(client, email="hotels-results-v2-provider-failure@viru.dev")
    headers = _auth(token)
    assert client.post("/api/v1/hotels/ingest/mock", headers=headers).status_code == 200

    monkeypatch.setenv("HOTEL_PROFILE", "staging_canary")
    monkeypatch.setenv("HOTEL_PROVIDER", "makcorps")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_ENABLED", "true")
    monkeypatch.setenv("HOTEL_PROVIDER_MAKCORPS_DAILY_REQUEST_BUDGET", "1")

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        hotel = db.query(HotelProperty).first()
        assert hotel is not None
        db.add(
            HotelProviderAlias(
                hotel_id=hotel.id,
                provider="makcorps",
                provider_hotel_id="failing-provider-hotel",
            )
        )
        db.commit()
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass

    class FailingProvider:
        provider_id = "makcorps"

        def fetch_hotel_rates(self, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "app.hotels.ingestion.resolve_hotel_provider",
        lambda **kwargs: FailingProvider(),
    )
    response = client.get(
        "/api/v1/hotels/v2/area-search",
        headers=headers,
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_km": 50,
            "check_in": "2026-07-10",
            "check_out": "2026-07-12",
            "use_provider": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["result_state"] == "partial"
    assert payload["meta"]["providers"][0]["status"] == "failed"
    assert payload["meta"]["providers"][0]["fallback_used"] is True
    assert payload["meta"]["warnings"][0]["code"] == "provider_unavailable"
    assert payload["data"]
