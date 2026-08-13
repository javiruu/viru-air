from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import register_and_token


def auth_headers(client: TestClient) -> dict[str, str]:
    token = register_and_token(client, email="rum@example.com", password="password123")
    return {"Authorization": f"Bearer {token}"}


def valid_hotel_rum_metadata() -> dict[str, str | int]:
    return {
        "schema_version": 1,
        "surface": "hoteles",
        "metric": "lcp",
        "value_bucket": "1000-2000ms",
        "rating": "good",
        "navigation_type": "navigate",
        "device_class": "mobile",
    }


def test_hotel_rum_event_is_persisted_when_metadata_is_allowlisted(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={"event_name": "hotel_rum_vitals", "metadata": valid_hotel_rum_metadata()},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hotel_rum_event_ignores_unknown_metadata_keys(client: TestClient) -> None:
    metadata = valid_hotel_rum_metadata()
    metadata["email"] = "private@example.com"
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={"event_name": "hotel_rum_vitals", "metadata": metadata},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_hotel_rum_event_rejects_boolean_schema_version(client: TestClient) -> None:
    metadata = valid_hotel_rum_metadata()
    metadata["schema_version"] = True
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={"event_name": "hotel_rum_vitals", "metadata": metadata},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_hotel_rum_event_ignores_metric_bucket_mismatch(client: TestClient) -> None:
    metadata = valid_hotel_rum_metadata()
    metadata["metric"] = "cls"
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={"event_name": "hotel_rum_vitals", "metadata": metadata},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_hotel_product_event_is_persisted_when_metadata_is_allowlisted(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={
            "event_name": "hotel_search_completed",
            "metadata": {
                "schema_version": 1,
                "surface": "hoteles",
                "result_state": "success",
                "result_count_bucket": "4-10",
                "provider_mode": "mock",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hotel_product_event_ignores_boolean_schema_version(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={
            "event_name": "hotel_search_completed",
            "metadata": {
                "schema_version": True,
                "surface": "hoteles",
                "result_state": "success",
                "result_count_bucket": "4-10",
                "provider_mode": "mock",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_hotel_product_event_ignores_unknown_metadata_keys(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={
            "event_name": "hotel_search_completed",
            "metadata": {
                "schema_version": 1,
                "surface": "hoteles",
                "result_state": "success",
                "result_count_bucket": "4-10",
                "provider_mode": "mock",
                "hotel_id": "private-id",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_unknown_ux_event_remains_ignored(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ux/events",
        headers=auth_headers(client),
        json={"event_name": "hotel_rum_vitals_private_raw", "metadata": {}},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
