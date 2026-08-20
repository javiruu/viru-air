from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def test_bulk_create_tracks_exact_dates_and_is_idempotent(client: TestClient) -> None:
    token = register_and_token(client, email="bulk-watch@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    dates = [str(date.today() + timedelta(days=offset)) for offset in (20, 23, 28)]
    payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "travel_dates": dates,
    }

    first = client.post("/api/v1/watchlist/bulk-create", headers=headers, json=payload)
    second = client.post("/api/v1/watchlist/bulk-create", headers=headers, json=payload)

    assert first.status_code == 200
    assert first.json()["created_dates"] == dates
    assert first.json()["existing_dates"] == []
    assert second.status_code == 200
    assert second.json()["created_dates"] == []
    assert second.json()["existing_dates"] == dates

    watches = client.get("/api/v1/watchlist", headers=headers)
    assert watches.status_code == 200
    assert {watch["travel_date_local"] for watch in watches.json()} == set(dates)


def test_bulk_create_rejects_more_than_fifteen_dates_without_creating_any(client: TestClient) -> None:
    token = register_and_token(client, email="bulk-watch-limit@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    dates = [str(date.today() + timedelta(days=offset)) for offset in range(20, 36)]

    response = client.post(
        "/api/v1/watchlist/bulk-create",
        headers=headers,
        json={"origin_iata": "MAD", "destination_iata": "DUB", "travel_dates": dates},
    )

    assert response.status_code == 422
    watches = client.get("/api/v1/watchlist", headers=headers)
    assert watches.status_code == 200
    assert watches.json() == []
