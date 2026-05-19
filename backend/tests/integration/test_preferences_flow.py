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
            "country_price_hint_mode_default": "median",
            "calendar_hint_bucket_mode_default": "guidelines",
            "calendar_hint_guideline_low_max_default": 90,
            "calendar_hint_guideline_mid_max_default": 150,
            "avoid_departure_before": "07:00",
            "depart_before_default": "22:00",
            "strict_filters_default": False,
            "preferred_currency": "EUR",
            "language": "es",
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "quiet_hours_timezone": "Europe/Madrid",
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
        "country_price_hint_mode_default": "median",
        "calendar_hint_bucket_mode_default": "guidelines",
        "calendar_hint_guideline_low_max_default": 90.0,
        "calendar_hint_guideline_mid_max_default": 150.0,
        "avoid_departure_before": "07:00",
        "depart_before_default": "22:00",
        "strict_filters_default": False,
        "preferred_currency": "EUR",
        "language": "es",
        "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
        "quiet_hours_timezone": "Europe/Madrid",
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
            "country_price_hint_mode_default": "min",
            "calendar_hint_bucket_mode_default": "guidelines",
            "calendar_hint_guideline_low_max_default": 100,
            "calendar_hint_guideline_mid_max_default": 90,
            "avoid_departure_before": "07:00",
            "depart_before_default": "25:00",
            "strict_filters_default": True,
            "preferred_currency": "EUR",
            "language": "es",
            "quiet_hours_enabled": False,
            "quiet_hours_start": "25:00",
            "quiet_hours_end": "08:00",
            "quiet_hours_timezone": "Europe/Madrid",
        },
    )

    assert response.status_code == 422


def test_preferences_convert_guideline_thresholds_when_currency_changes(client: TestClient) -> None:
    token = register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    first_put = client.put(
        "/api/v1/preferences/search",
        headers=headers,
        json={
            "default_radius_km": 150,
            "include_stops_default": False,
            "include_nearby_origins_default": False,
            "include_nearby_destinations_default": False,
            "country_price_hint_mode_default": "min",
            "calendar_hint_bucket_mode_default": "guidelines",
            "calendar_hint_guideline_low_max_default": 90,
            "calendar_hint_guideline_mid_max_default": 150,
            "avoid_departure_before": None,
            "depart_before_default": None,
            "strict_filters_default": True,
            "preferred_currency": "EUR",
            "language": "es",
            "quiet_hours_enabled": False,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "quiet_hours_timezone": "Europe/Madrid",
        },
    )
    assert first_put.status_code == 200

    second_put = client.put(
        "/api/v1/preferences/search",
        headers=headers,
        json={
            "default_radius_km": 150,
            "include_stops_default": False,
            "include_nearby_origins_default": False,
            "include_nearby_destinations_default": False,
            "country_price_hint_mode_default": "min",
            "calendar_hint_bucket_mode_default": "guidelines",
            "calendar_hint_guideline_low_max_default": 90,
            "calendar_hint_guideline_mid_max_default": 150,
            "avoid_departure_before": None,
            "depart_before_default": None,
            "strict_filters_default": True,
            "preferred_currency": "USD",
            "language": "es",
            "quiet_hours_enabled": False,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "quiet_hours_timezone": "Europe/Madrid",
        },
    )
    assert second_put.status_code == 200

    get = client.get("/api/v1/preferences/search", headers=headers)
    assert get.status_code == 200
    data = get.json()
    assert data["preferred_currency"] == "USD"
    assert data["calendar_hint_guideline_low_max_default"] == 96.77
    assert data["calendar_hint_guideline_mid_max_default"] == 161.29
