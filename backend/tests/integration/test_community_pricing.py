from collections.abc import Generator
from datetime import date, timedelta

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightWatch
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


def _headers_for(client: TestClient, email: str) -> dict[str, str]:
    token = register_and_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


def _create_watch(
    client: TestClient,
    headers: dict[str, str],
    *,
    origin: str = "AGP",
    destination: str = "FCO",
    days_from_today: int = 30,
) -> str:
    response = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": origin,
            "destination_iata": destination,
            "travel_date_local": str(date.today() + timedelta(days=days_from_today)),
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _open_db() -> tuple[Session, Generator[Session, None, None]]:
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    return db, generator


def _close_db(db: Session, generator: Generator[Session, None, None]) -> None:
    db.close()
    try:
        next(generator)
    except StopIteration:
        return


def _set_travel_date(watch_id: str, travel_date: date) -> None:
    db, generator = _open_db()
    try:
        watch = db.scalar(select(FlightWatch).where(FlightWatch.id == watch_id))
        assert watch is not None
        watch.travel_date_local = travel_date
        db.commit()
    finally:
        _close_db(db, generator)


def _mark_purchased(
    client: TestClient,
    headers: dict[str, str],
    watch_id: str,
) -> Response:
    response = client.post(f"/api/v1/watchlist/{watch_id}/mark-purchased", headers=headers)
    assert response.status_code == 200
    return response


def _report_price(
    client: TestClient,
    headers: dict[str, str],
    watch_id: str,
    price: float,
) -> Response:
    response = client.put(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=headers,
        json={"flew": True, "price_per_traveler": price},
    )
    assert response.status_code == 200
    return response


def test_mark_purchased_and_report_are_owner_scoped(client: TestClient) -> None:
    owner_headers = _headers_for(client, "community-owner@viru.dev")
    other_headers = _headers_for(client, "community-other@viru.dev")
    watch_id = _create_watch(client, owner_headers)

    forbidden_purchase = client.post(
        f"/api/v1/watchlist/{watch_id}/mark-purchased",
        headers=other_headers,
    )
    forbidden_report = client.put(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=other_headers,
        json={"flew": False},
    )

    assert forbidden_purchase.status_code == 404
    assert forbidden_report.status_code == 404

    purchased = _mark_purchased(client, owner_headers, watch_id).json()
    assert purchased["status"] == "purchased"
    assert purchased["community_pricing"]["eligible"] is True
    assert purchased["community_pricing"]["trigger_reason"] == "purchased"
    assert purchased["community_pricing"]["response"] is None

    saved = client.put(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=owner_headers,
        json={"flew": False},
    )
    assert saved.status_code == 200
    assert saved.json()["community_pricing"]["response"] == {
        "flew": False,
        "price_per_traveler": None,
        "currency": "EUR",
    }

    forbidden_delete = client.delete(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=other_headers,
    )
    assert forbidden_delete.status_code == 404


def test_community_price_validates_flew_and_price_consistency(client: TestClient) -> None:
    headers = _headers_for(client, "community-validation@viru.dev")
    watch_id = _create_watch(client, headers, destination="DUB")
    _mark_purchased(client, headers, watch_id)

    missing_price = client.put(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=headers,
        json={"flew": True},
    )
    price_without_flight = client.put(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=headers,
        json={"flew": False, "price_per_traveler": 79.5},
    )
    invalid_price = client.put(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=headers,
        json={"flew": True, "price_per_traveler": 0},
    )

    assert missing_price.status_code == 422
    assert price_without_flight.status_code == 422
    assert invalid_price.status_code == 422


def test_expired_watch_is_pending_without_status_mutation(client: TestClient) -> None:
    headers = _headers_for(client, "community-expired@viru.dev")
    watch_id = _create_watch(client, headers, destination="LIS")
    _set_travel_date(watch_id, date.today() - timedelta(days=1))

    listing = client.get("/api/v1/watchlist", headers=headers)

    assert listing.status_code == 200
    watch = listing.json()[0]
    assert watch["id"] == watch_id
    assert watch["status"] == "active"
    assert watch["community_pricing"]["eligible"] is True
    assert watch["community_pricing"]["trigger_reason"] == "expired"
    assert watch["community_pricing"]["response"] is None


def test_route_aggregate_is_hidden_until_three_distinct_users(client: TestClient) -> None:
    travel_date = date.today() - timedelta(days=20)
    prices = [67.0, 78.5, 89.0]
    rows: list[tuple[dict[str, str], str]] = []

    for index in range(3):
        headers = _headers_for(client, f"community-threshold-{index}@viru.dev")
        watch_id = _create_watch(client, headers)
        _set_travel_date(watch_id, travel_date)
        _mark_purchased(client, headers, watch_id)
        rows.append((headers, watch_id))

    first = _report_price(client, rows[0][0], rows[0][1], prices[0]).json()
    second = _report_price(client, rows[1][0], rows[1][1], prices[1]).json()

    assert first["community_pricing"]["aggregate"]["sample_size"] == 1
    assert first["community_pricing"]["aggregate"]["is_public"] is False
    assert first["community_pricing"]["aggregate"]["min_price"] is None
    assert second["community_pricing"]["aggregate"]["sample_size"] == 2
    assert second["community_pricing"]["aggregate"]["max_price"] is None

    third = _report_price(client, rows[2][0], rows[2][1], prices[2]).json()
    aggregate = third["community_pricing"]["aggregate"]
    assert aggregate == {
        "sample_size": 3,
        "minimum_sample_size": 3,
        "is_public": True,
        "min_price": 67.0,
        "max_price": 89.0,
        "currency": "EUR",
    }

    refreshed_first = client.get("/api/v1/watchlist", headers=rows[0][0]).json()[0]
    assert refreshed_first["community_pricing"]["aggregate"] == aggregate


def test_aggregate_excludes_reverse_route_and_reports_older_than_twelve_months(
    client: TestClient,
) -> None:
    included_headers = _headers_for(client, "community-included@viru.dev")
    included_watch = _create_watch(client, included_headers)
    _set_travel_date(included_watch, date.today() - timedelta(days=10))
    _mark_purchased(client, included_headers, included_watch)
    included = _report_price(client, included_headers, included_watch, 72.0).json()

    reverse_headers = _headers_for(client, "community-reverse@viru.dev")
    reverse_watch = _create_watch(
        client,
        reverse_headers,
        origin="FCO",
        destination="AGP",
    )
    _set_travel_date(reverse_watch, date.today() - timedelta(days=10))
    _mark_purchased(client, reverse_headers, reverse_watch)
    _report_price(client, reverse_headers, reverse_watch, 15.0)

    old_headers = _headers_for(client, "community-old@viru.dev")
    old_watch = _create_watch(client, old_headers, days_from_today=31)
    _set_travel_date(old_watch, date.today() - timedelta(days=366))
    _mark_purchased(client, old_headers, old_watch)
    _report_price(client, old_headers, old_watch, 999.0)

    listing = client.get("/api/v1/watchlist", headers=included_headers)
    aggregate = listing.json()[0]["community_pricing"]["aggregate"]
    assert included["community_pricing"]["aggregate"]["sample_size"] == 1
    assert aggregate["sample_size"] == 1
    assert aggregate["is_public"] is False
    assert aggregate["min_price"] is None
    assert aggregate["max_price"] is None


def test_response_can_be_edited_and_deleted(client: TestClient) -> None:
    headers = _headers_for(client, "community-edit@viru.dev")
    watch_id = _create_watch(client, headers, destination="PMI")
    _set_travel_date(watch_id, date.today() - timedelta(days=5))
    _mark_purchased(client, headers, watch_id)

    initial = _report_price(client, headers, watch_id, 54.0).json()
    edited = _report_price(client, headers, watch_id, 61.25).json()
    deleted = client.delete(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=headers,
    )

    assert initial["community_pricing"]["response"]["price_per_traveler"] == 54.0
    assert edited["community_pricing"]["response"]["price_per_traveler"] == 61.25
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "ok"
    listing = client.get("/api/v1/watchlist", headers=headers)
    assert listing.json()[0]["community_pricing"]["response"] is None
