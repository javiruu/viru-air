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
            "include_nearby_origins_default": True,
            "include_nearby_destinations_default": False,
            "avoid_departure_before": "07:00",
            "depart_before_default": "22:00",
            "strict_filters_default": False,
            "preferred_currency": "EUR",
            "language": "es",
        },
    )
    assert put.status_code == 200

    get = client.get("/api/v1/preferences", headers=headers)
    assert get.status_code == 200
    assert get.json() == {
        "default_radius_km": 180,
        "include_stops_default": True,
        "include_nearby_origins_default": True,
        "include_nearby_destinations_default": False,
        "avoid_departure_before": "07:00",
        "depart_before_default": "22:00",
        "strict_filters_default": False,
        "preferred_currency": "EUR",
        "language": "es",
    }


def test_preferences_reject_invalid_depart_before_default(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/api/v1/preferences/search",
        headers=headers,
        json={
            "default_radius_km": 150,
            "include_stops_default": False,
            "include_nearby_origins_default": False,
            "include_nearby_destinations_default": False,
            "avoid_departure_before": "07:00",
            "depart_before_default": "25:00",
            "strict_filters_default": True,
            "preferred_currency": "EUR",
            "language": "es",
        },
    )

    assert response.status_code == 422
