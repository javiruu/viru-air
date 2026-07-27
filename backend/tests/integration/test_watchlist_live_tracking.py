from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from threading import Event
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    FlightOfferCacheEntry,
    FlightOperationalSnapshot,
    FlightPriceObservation,
    PriceSnapshot,
    WatchTrackedFlightLeg,
)
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


class _ProviderResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def _open_test_db_session():
    override = app.dependency_overrides[get_db]
    generator = override()
    return next(generator), generator


def _close_test_db_session(generator) -> None:
    try:
        next(generator)
    except StopIteration:
        pass


def test_saved_quick_search_result_links_exact_leg_for_live_tracking(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=14)
    token = register_and_token(client, email="live-linked@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    save_response = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "FR9602",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": f"{travel_date.isoformat()}T08:30:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T10:55:00Z",
                }
            ],
        },
    )

    assert save_response.status_code == 200
    assert save_response.json()["tracking_identity"] == "linked"
    watch_id = save_response.json()["watch_id"]

    live_response = client.get(f"/api/v1/watchlist/{watch_id}/live", headers=headers)

    assert live_response.status_code == 200
    payload = live_response.json()
    assert payload["watch_id"] == watch_id
    assert payload["coverage"] == "not_configured"
    assert payload["provider_status"] == "not_configured"
    assert payload["legs"][0]["identity"]["flight_number"] == "FR9602"
    assert payload["legs"][0]["identity"]["origin_iata"] == "MAD"
    assert payload["legs"][0]["operational"] is None


def test_legacy_watch_without_exact_identity_reports_identity_missing(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=21)
    token = register_and_token(client, email="live-legacy@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "AGP",
            "destination_iata": "DUB",
            "travel_date_local": travel_date.isoformat(),
            "target_price": 55,
        },
    )
    assert create_response.status_code == 200

    live_response = client.get(
        f"/api/v1/watchlist/{create_response.json()['id']}/live",
        headers=headers,
    )

    assert live_response.status_code == 200
    assert live_response.json()["coverage"] == "identity_missing"
    assert live_response.json()["provider_status"] == "no_match"
    assert live_response.json()["legs"] == []


def test_live_tracking_links_unique_older_identity_when_newer_snapshot_has_no_match(
    client: TestClient,
) -> None:
    travel_date = date.today() + timedelta(days=22)
    departure_at = datetime.combine(travel_date, datetime.min.time()).replace(hour=16, minute=55)
    token = register_and_token(client, email="live-fare-memory-link@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    create_response = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "VCE",
            "travel_date_local": travel_date.isoformat(),
            "target_price": 56.99,
        },
    )
    assert create_response.status_code == 200
    watch_id = create_response.json()["id"]

    db, generator = _open_test_db_session()
    try:
        captured_at = utc_now_naive()
        db.add(
            PriceSnapshot(
                watch_id=watch_id,
                captured_at_utc=captured_at,
                raw_price=56.99,
                raw_currency="EUR",
                provider="ryanair-public-fares",
                departure_time_local="16:55",
            )
        )
        db.add(
            PriceSnapshot(
                watch_id=watch_id,
                captured_at_utc=captured_at + timedelta(seconds=1),
                raw_price=62.57,
                raw_currency="EUR",
                provider="vueling-public-availability",
                departure_time_local="19:25",
            )
        )
        offer = FlightOfferCacheEntry(
            offer_fingerprint="fsm_offer_live_fare_memory_link",
            flight_instance_fingerprint="fsm_flight_live_fare_memory_link",
            provider="ryanair-public-fares",
            carrier="FR",
            carrier_code="FR",
            flight_number="FR1206",
            origin_airport="MAD",
            destination_airport="VCE",
            departure_at=departure_at,
            arrival_at=departure_at + timedelta(hours=2, minutes=25),
            departure_time_local="16:55",
            arrival_time_local="19:20",
            stops_count=0,
        )
        db.add(offer)
        db.flush()
        db.add(
            FlightPriceObservation(
                offer_id=offer.id,
                provider="ryanair-public-fares",
                price_amount=56.99,
                currency="EUR",
                observed_at=utc_now_naive(),
            )
        )
        db.commit()
    finally:
        db.close()
        _close_test_db_session(generator)

    live_response = client.get(f"/api/v1/watchlist/{watch_id}/live?refresh=false", headers=headers)

    assert live_response.status_code == 200
    payload = live_response.json()
    assert payload["coverage"] == "not_configured"
    assert payload["legs"][0]["identity"]["flight_number"] == "FR1206"
    assert payload["legs"][0]["identity"]["scheduled_departure_at"] is None


def test_live_tracking_does_not_guess_between_fare_memory_flights(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=23)
    departure_at = datetime.combine(travel_date, datetime.min.time()).replace(hour=16, minute=55)
    token = register_and_token(client, email="live-fare-memory-ambiguous@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "VCE",
            "travel_date_local": travel_date.isoformat(),
            "target_price": 56.99,
        },
    )
    watch_id = created.json()["id"]

    db, generator = _open_test_db_session()
    try:
        db.add(
            PriceSnapshot(
                watch_id=watch_id,
                raw_price=56.99,
                raw_currency="EUR",
                provider="ryanair-public-fares",
                departure_time_local="16:55",
            )
        )
        for suffix, flight_number in (("a", "FR1206"), ("b", "FR1208")):
            offer = FlightOfferCacheEntry(
                offer_fingerprint=f"fsm_offer_live_fare_memory_ambiguous_{suffix}",
                flight_instance_fingerprint=f"fsm_flight_live_fare_memory_ambiguous_{suffix}",
                provider="ryanair-public-fares",
                carrier="FR",
                carrier_code="FR",
                flight_number=flight_number,
                origin_airport="MAD",
                destination_airport="VCE",
                departure_at=departure_at,
                arrival_at=departure_at + timedelta(hours=2, minutes=25),
                departure_time_local="16:55",
                arrival_time_local="19:20",
                stops_count=0,
            )
            db.add(offer)
            db.flush()
            db.add(
                FlightPriceObservation(
                    offer_id=offer.id,
                    provider="ryanair-public-fares",
                    price_amount=56.99,
                    currency="EUR",
                    observed_at=utc_now_naive(),
                )
            )
        db.commit()
    finally:
        db.close()
        _close_test_db_session(generator)

    live_response = client.get(f"/api/v1/watchlist/{watch_id}/live?refresh=false", headers=headers)

    assert live_response.status_code == 200
    assert live_response.json()["coverage"] == "identity_missing"
    db, generator = _open_test_db_session()
    try:
        legs = db.scalars(
            select(WatchTrackedFlightLeg).where(WatchTrackedFlightLeg.watch_id == watch_id)
        ).all()
    finally:
        db.close()
        _close_test_db_session(generator)
    assert legs == []


def test_live_tracking_hides_watch_owned_by_another_user(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=10)
    owner_token = register_and_token(client, email="live-owner@viru.dev")
    other_token = register_and_token(client, email="live-other@viru.dev")
    create_response = client.post(
        "/api/v1/watchlist",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "origin_iata": "BCN",
            "destination_iata": "ORY",
            "travel_date_local": travel_date.isoformat(),
            "target_price": 60,
        },
    )
    assert create_response.status_code == 200

    live_response = client.get(
        f"/api/v1/watchlist/{create_response.json()['id']}/live",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert live_response.status_code == 404


def test_live_tracking_reuses_fresh_operational_snapshot_with_position(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=1)
    token = register_and_token(client, email="live-cached@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    save_response = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "FR9602",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": f"{travel_date.isoformat()}T08:30:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T10:55:00Z",
                }
            ],
        },
    )
    watch_id = save_response.json()["watch_id"]
    now = utc_now_naive()
    db, generator = _open_test_db_session()
    try:
        leg = db.scalar(
            select(WatchTrackedFlightLeg).where(WatchTrackedFlightLeg.watch_id == watch_id)
        )
        assert leg is not None
        db.add(
            FlightOperationalSnapshot(
                flight_instance_fingerprint=leg.flight_instance_fingerprint,
                provider="aviationstack",
                provider_flight_id="flight-9602",
                flight_number="FR9602",
                callsign="RYR9602",
                status="active",
                status_raw="active",
                observed_at=now,
                expires_at=now + timedelta(minutes=2),
                scheduled_departure_at=datetime.combine(travel_date, datetime.min.time()).replace(
                    hour=8,
                    minute=30,
                ),
                estimated_arrival_at=datetime.combine(travel_date, datetime.min.time()).replace(
                    hour=11,
                    minute=5,
                ),
                departure_terminal="1",
                departure_gate="B12",
                latitude=41.123456,
                longitude=2.123456,
                altitude_m=9100,
                speed_mps=220,
                heading_deg=94,
                on_ground=False,
                data_quality="observed",
            )
        )
        db.commit()
    finally:
        db.close()
        _close_test_db_session(generator)

    live_response = client.get(f"/api/v1/watchlist/{watch_id}/live", headers=headers)

    assert live_response.status_code == 200
    payload = live_response.json()
    assert payload["coverage"] == "live"
    assert payload["provider_status"] == "ok"
    assert payload["generated_at"].endswith("Z")
    operational = payload["legs"][0]["operational"]
    assert operational["status"] == "active"
    assert operational["freshness"] == "fresh"
    assert operational["observed_at"].endswith("Z")
    assert operational["departure"]["scheduled_at"].endswith("Z")
    assert operational["departure"]["gate"] == "B12"
    assert operational["position"]["latitude"] == 41.123456
    assert operational["position"]["heading_deg"] == 94.0


def test_live_tracking_fetches_provider_once_then_reuses_shared_cache(
    client: TestClient,
    monkeypatch,
) -> None:
    travel_date = date.today() + timedelta(days=1)
    departure_at = f"{travel_date.isoformat()}T08:30:00+00:00"
    arrival_at = f"{travel_date.isoformat()}T10:55:00+00:00"
    token = register_and_token(client, email="live-provider@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    save_response = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "FR9602",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": departure_at,
                    "arrival_at": arrival_at,
                }
            ],
        },
    )
    watch_id = save_response.json()["watch_id"]
    provider_calls = 0

    def fake_get(*args, **kwargs) -> _ProviderResponse:
        nonlocal provider_calls
        provider_calls += 1
        return _ProviderResponse(
            200,
            {
                "data": [
                    {
                        "flight_date": travel_date.isoformat(),
                        "flight_status": "active",
                        "departure": {
                            "iata": "MAD",
                            "scheduled": departure_at,
                            "actual": departure_at,
                            "terminal": "1",
                            "gate": "B12",
                            "delay": 0,
                        },
                        "arrival": {
                            "iata": "FCO",
                            "scheduled": arrival_at,
                            "estimated": f"{travel_date.isoformat()}T11:05:00+00:00",
                            "terminal": "3",
                            "gate": None,
                            "delay": 10,
                        },
                        "airline": {"iata": "FR"},
                        "flight": {"number": "9602", "iata": "FR9602", "icao": "RYR9602"},
                        "aircraft": {
                            "registration": "EI-TEST",
                            "iata": "B738",
                            "icao": "B738",
                            "icao24": "4CA123",
                        },
                        "live": {
                            "updated": datetime.now().astimezone().isoformat(),
                            "latitude": 41.123456,
                            "longitude": 2.123456,
                            "altitude": 9100,
                            "direction": 94,
                            "speed_horizontal": 220,
                            "is_ground": False,
                        },
                    }
                ]
            },
        )

    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "test-key")
    monkeypatch.setattr("requests.Session.get", fake_get)

    first_response = client.get(f"/api/v1/watchlist/{watch_id}/live", headers=headers)
    second_response = client.get(f"/api/v1/watchlist/{watch_id}/live", headers=headers)

    assert first_response.status_code == 200
    assert first_response.json()["coverage"] == "live"
    assert first_response.json()["legs"][0]["operational"]["status"] == "active"
    assert first_response.json()["legs"][0]["operational"]["arrival"]["delay_minutes"] == 10
    assert second_response.status_code == 200
    assert second_response.json()["coverage"] == "live"
    assert provider_calls == 1


def test_resaving_route_without_legs_preserves_existing_tracking_identity(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=2)
    token = register_and_token(client, email="live-preserve@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    base_payload = {
        "origin_iata": "MAD",
        "destination_iata": "FCO",
        "travel_date": travel_date.isoformat(),
        "price_total": 72.5,
        "currency": "EUR",
    }
    first = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            **base_payload,
            "legs": [
                {
                    "flight_number": "FR9602",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": f"{travel_date.isoformat()}T08:30:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T10:55:00Z",
                }
            ],
        },
    )
    second = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={**base_payload, "price_total": 69.0},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["created_or_existing"] == "existing"
    assert second.json()["tracking_identity"] == "linked"
    live = client.get(f"/api/v1/watchlist/{first.json()['watch_id']}/live", headers=headers)
    assert live.json()["legs"][0]["identity"]["flight_number"] == "FR9602"


def test_save_result_rejects_more_than_eight_tracking_legs(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=3)
    token = register_and_token(client, email="live-too-many-legs@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    legs = [
        {
            "flight_number": f"FR96{index:02d}",
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "departure_at": f"{travel_date.isoformat()}T08:30:00Z",
            "arrival_at": f"{travel_date.isoformat()}T10:55:00Z",
        }
        for index in range(9)
    ]

    response = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": legs,
        },
    )

    assert response.status_code == 422


def test_concurrent_live_requests_share_one_provider_refresh(
    client: TestClient,
    monkeypatch,
) -> None:
    travel_date = date.today() + timedelta(days=1)
    departure_at = f"{travel_date.isoformat()}T08:30:00+00:00"
    arrival_at = f"{travel_date.isoformat()}T10:55:00+00:00"
    token = register_and_token(client, email="live-concurrent@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "FR9602",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": departure_at,
                    "arrival_at": arrival_at,
                }
            ],
        },
    )
    watch_id = saved.json()["watch_id"]
    provider_started = Event()
    release_provider = Event()
    provider_calls = 0

    def fake_get(*args, **kwargs) -> _ProviderResponse:
        nonlocal provider_calls
        provider_calls += 1
        provider_started.set()
        assert release_provider.wait(timeout=3)
        return _ProviderResponse(
            200,
            {
                "data": [
                    {
                        "flight_date": travel_date.isoformat(),
                        "flight_status": "active",
                        "departure": {"iata": "MAD", "scheduled": departure_at},
                        "arrival": {"iata": "FCO", "scheduled": arrival_at},
                        "airline": {"iata": "FR"},
                        "flight": {"number": "9602", "iata": "FR9602"},
                        "live": {
                            "updated": datetime.now().astimezone().isoformat(),
                            "latitude": 41.1,
                            "longitude": 2.1,
                        },
                    }
                ]
            },
        )

    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "test-key")
    monkeypatch.setattr("requests.Session.get", fake_get)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            client.get,
            f"/api/v1/watchlist/{watch_id}/live",
            headers=headers,
        )
        assert provider_started.wait(timeout=3)
        second_future = executor.submit(
            client.get,
            f"/api/v1/watchlist/{watch_id}/live",
            headers=headers,
        )
        second_response = second_future.result(timeout=3)
        release_provider.set()
        first_response = first_future.result(timeout=3)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["coverage"] == "live"
    assert second_response.json()["coverage"] == "temporarily_unavailable"
    assert provider_calls == 1


def test_repeated_stale_provider_observation_is_deduplicated(
    client: TestClient,
    monkeypatch,
) -> None:
    travel_date = date.today() + timedelta(days=1)
    departure_at = f"{travel_date.isoformat()}T08:30:00+00:00"
    arrival_at = f"{travel_date.isoformat()}T10:55:00+00:00"
    observed_at = (datetime.now().astimezone() - timedelta(days=1)).isoformat()
    token = register_and_token(client, email="live-dedupe@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "FR9602",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": departure_at,
                    "arrival_at": arrival_at,
                }
            ],
        },
    )
    watch_id = saved.json()["watch_id"]

    def fake_get(*args, **kwargs) -> _ProviderResponse:
        return _ProviderResponse(
            200,
            {
                "data": [
                    {
                        "flight_date": travel_date.isoformat(),
                        "flight_status": "active",
                        "departure": {"iata": "MAD", "scheduled": departure_at},
                        "arrival": {"iata": "FCO", "scheduled": arrival_at},
                        "airline": {"iata": "FR"},
                        "flight": {"number": "9602", "iata": "FR9602"},
                        "live": {
                            "updated": observed_at,
                            "latitude": 41.1,
                            "longitude": 2.1,
                        },
                    }
                ]
            },
        )

    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "test-key")
    monkeypatch.setattr("requests.Session.get", fake_get)
    first = client.get(f"/api/v1/watchlist/{watch_id}/live", headers=headers)
    second = client.get(f"/api/v1/watchlist/{watch_id}/live", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    db, generator = _open_test_db_session()
    try:
        snapshot_count = db.scalar(select(func.count()).select_from(FlightOperationalSnapshot))
    finally:
        db.close()
        _close_test_db_session(generator)
    assert snapshot_count == 1


@pytest.mark.parametrize(
    ("status_code", "payload", "expected_status", "expected_coverage"),
    [
        (200, {"data": []}, "no_match", "no_coverage"),
        (429, {}, "rate_limited", "temporarily_unavailable"),
        (503, {}, "unavailable", "temporarily_unavailable"),
    ],
)
def test_negative_provider_outcomes_use_persistent_cooldown(
    client: TestClient,
    monkeypatch,
    status_code: int,
    payload: dict[str, Any],
    expected_status: str,
    expected_coverage: str,
) -> None:
    travel_date = date.today() + timedelta(days=4)
    token = register_and_token(client, email=f"live-cooldown-{status_code}@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "FR9602",
                    "origin_iata": "MAD",
                    "destination_iata": "FCO",
                    "departure_at": f"{travel_date.isoformat()}T08:30:00+00:00",
                    "arrival_at": f"{travel_date.isoformat()}T10:55:00+00:00",
                }
            ],
        },
    )
    provider_calls = 0

    def fake_get(*args, **kwargs) -> _ProviderResponse:
        nonlocal provider_calls
        provider_calls += 1
        return _ProviderResponse(status_code, payload)

    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "test-key")
    monkeypatch.setattr("requests.Session.get", fake_get)
    live_url = f"/api/v1/watchlist/{saved.json()['watch_id']}/live"

    first = client.get(live_url, headers=headers)
    second = client.get(live_url, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["provider_status"] == expected_status
    assert second.json()["provider_status"] == expected_status
    assert first.json()["coverage"] == expected_coverage
    assert second.json()["coverage"] == expected_coverage
    assert provider_calls == 1


def test_save_result_rejects_tracking_legs_outside_saved_route(client: TestClient) -> None:
    travel_date = date.today() + timedelta(days=5)
    token = register_and_token(client, email="live-invalid-chain@viru.dev")

    response = client.post(
        "/api/v1/search/save-result",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "origin_iata": "MAD",
            "destination_iata": "FCO",
            "travel_date": travel_date.isoformat(),
            "price_total": 72.5,
            "currency": "EUR",
            "legs": [
                {
                    "flight_number": "FR1234",
                    "origin_iata": "LHR",
                    "destination_iata": "JFK",
                    "departure_at": f"{travel_date.isoformat()}T08:30:00Z",
                    "arrival_at": f"{travel_date.isoformat()}T12:30:00Z",
                }
            ],
        },
    )

    assert response.status_code == 422
