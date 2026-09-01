from collections.abc import Generator
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import FlightWatch, QuickSearchPopularityDaily
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


def _headers_for(client: TestClient, email: str) -> dict[str, str]:
    token = register_and_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


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


def _seed_popularity(
    origin: str,
    destination: str,
    count: int,
    *,
    days_ago: int = 0,
) -> None:
    db, generator = _open_db()
    try:
        now = datetime.now()
        db.add(
            QuickSearchPopularityDaily(
                search_date=date.today() - timedelta(days=days_ago),
                origin_iata=origin,
                destination_iata=destination,
                currency="EUR",
                search_count=count,
                first_searched_at=now,
                last_searched_at=now,
            )
        )
        db.commit()
    finally:
        _close_db(db, generator)


def _create_watch(
    client: TestClient,
    headers: dict[str, str],
    origin: str,
    destination: str,
) -> str:
    response = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": origin,
            "destination_iata": destination,
            "travel_date_local": str(date.today() + timedelta(days=30)),
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _set_past_date(watch_id: str) -> None:
    db, generator = _open_db()
    try:
        watch = db.scalar(select(FlightWatch).where(FlightWatch.id == watch_id))
        assert watch is not None
        watch.travel_date_local = date.today() - timedelta(days=10)
        db.commit()
    finally:
        _close_db(db, generator)


def _report_price(
    client: TestClient,
    headers: dict[str, str],
    watch_id: str,
    price: float,
) -> None:
    response = client.put(
        f"/api/v1/watchlist/{watch_id}/community-price",
        headers=headers,
        json={"flew": True, "price_per_traveler": price},
    )
    assert response.status_code == 200


def test_popular_routes_use_exact_seven_day_window_and_stable_top_twenty_percent(
    client: TestClient,
) -> None:
    headers = _headers_for(client, "community-popular@viru.dev")
    routes = [
        ("MAD", "BCN", 20),
        ("MAD", "LIS", 15),
        ("AGP", "FCO", 10),
        ("SVQ", "VCE", 8),
        ("ALC", "PMI", 5),
        ("DUB", "LPA", 5),
    ]
    for origin, destination, count in routes:
        _seed_popularity(origin, destination, count)
    _seed_popularity("ZZZ", "BCN", 99)
    _seed_popularity("LPA", "TFN", 99, days_ago=7)

    response = client.get("/api/v1/community/routes/popular", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["window_days"] == 7
    assert [(row["origin_iata"], row["destination_iata"]) for row in payload["routes"]] == [
        (origin, destination) for origin, destination, _ in routes
    ]
    assert all("ZZZ" not in (row["origin_iata"], row["destination_iata"]) for row in payload["routes"])
    assert all(row["is_trending"] is True for row in payload["routes"][:2])
    assert all(row["is_trending"] is False for row in payload["routes"][2:])


def test_route_insights_publish_only_public_price_ranges(client: TestClient) -> None:
    requester = _headers_for(client, "community-insight-reader@viru.dev")
    for index, price in enumerate((45.0, 61.0, 78.0)):
        headers = _headers_for(client, f"community-insight-{index}@viru.dev")
        watch_id = _create_watch(client, headers, "MAD", "BCN")
        _set_past_date(watch_id)
        _report_price(client, headers, watch_id, price)
    for index, price in enumerate((52.0, 64.0)):
        headers = _headers_for(client, f"community-private-insight-{index}@viru.dev")
        watch_id = _create_watch(client, headers, "BCN", "MAD")
        _set_past_date(watch_id)
        _report_price(client, headers, watch_id, price)

    response = client.post(
        "/api/v1/community/routes/insights",
        headers=requester,
        json={
            "routes": [
                {"origin_iata": "mad", "destination_iata": "bcn"},
                {"origin_iata": "BCN", "destination_iata": "MAD"},
            ]
        },
    )

    assert response.status_code == 200
    public, reverse = response.json()["routes"]
    assert public["sample_size"] == 3
    assert public["min_price"] == 45.0
    assert public["max_price"] == 78.0
    assert reverse["sample_size"] == 0
    assert reverse["min_price"] is None
    assert reverse["max_price"] is None


def test_route_insights_reject_non_ascii_iata(client: TestClient) -> None:
    headers = _headers_for(client, "community-invalid-iata@viru.dev")

    response = client.post(
        "/api/v1/community/routes/insights",
        headers=headers,
        json={
            "routes": [
                {"origin_iata": "АБВ", "destination_iata": "MAD"},
            ]
        },
    )

    assert response.status_code == 422


def test_related_routes_require_three_distinct_users(client: TestClient) -> None:
    requester = _headers_for(client, "community-related-reader@viru.dev")
    for index in range(3):
        headers = _headers_for(client, f"community-related-{index}@viru.dev")
        _create_watch(client, headers, "MAD", "BCN")
        _create_watch(client, headers, "MAD", "LIS")
    private_headers = _headers_for(client, "community-related-private@viru.dev")
    _create_watch(client, private_headers, "MAD", "BCN")
    _create_watch(client, private_headers, "SVQ", "BIO")

    response = client.get(
        "/api/v1/community/routes/MAD/BCN/related",
        headers=requester,
    )

    assert response.status_code == 200
    assert response.json()["routes"] == [
        {
            "origin_iata": "MAD",
            "destination_iata": "LIS",
            "travelers_count": 3,
        }
    ]
