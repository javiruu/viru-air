from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def test_preferences_roundtrip(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    put = client.put(
        "/api/v1/preferences",
        headers=headers,
        json={
            "default_radius_km": 180,
            "include_stops_default": True,
            "avoid_departure_before": "07:00",
            "preferred_currency": "EUR",
            "language": "es",
        },
    )
    assert put.status_code == 200

    get = client.get("/api/v1/preferences", headers=headers)
    assert get.status_code == 200
    assert get.json()["default_radius_km"] == 180
