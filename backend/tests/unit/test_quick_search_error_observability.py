from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_quick_search_invalid_seed_returns_traceable_error_envelope() -> None:
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "TSF", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": "2026-06-14", "flex_before": 0, "flex_after": 0},
        },
        headers={"x-correlation-id": "corrtest123"},
    )

    assert response.status_code == 400
    payload = response.json()

    assert payload["code"] == "quick_search_invalid_request"
    assert payload["message"] == "Quick-search request rejected by backend validation."
    assert payload["correlation_id"] == "corrtest123"
    assert len(payload["details"]) == 1
    assert payload["details"][0]["reason"] == "unknown_seed_iata:TSF"
    assert payload["details"][0]["reason_code"] == "unknown_seed_iata"
    assert payload["details"][0]["rejected_value"] == "TSF"
    assert payload["details"][0]["query_trace_id"].startswith("qs_")


def test_quick_search_invalid_iata_during_normalization_returns_traceable_error_envelope() -> None:
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin_iata": "AG",
            "destination_iata": "DUB",
            "travel_date": "2026-06-14",
        },
        headers={"x-correlation-id": "corrtest124"},
    )

    assert response.status_code == 400
    payload = response.json()

    assert payload["code"] == "quick_search_invalid_request"
    assert payload["message"] == "Quick-search request rejected during request normalization."
    assert payload["correlation_id"] == "corrtest124"
    assert payload["details"][0]["reason"] == "iata_invalido"
    assert payload["details"][0]["query_trace_id"].startswith("qs_")
    assert payload["details"][0]["raw_payload"]["origin_iata"] == "AG"


def test_deeplink_invalid_iata_returns_traceable_error_envelope() -> None:
    response = client.get(
        "/api/v1/search/deeplink?origin_iata=AG&destination_iata=DUB&date_out=2026-06-14&adults=1&teens=0&children=0&infants=0&locale=es-es",
        headers={"x-correlation-id": "corrtest125"},
    )

    assert response.status_code == 400
    payload = response.json()

    assert payload["code"] == "deeplink_invalid_request"
    assert payload["message"] == "Deep-link request rejected by backend validation."
    assert payload["correlation_id"] == "corrtest125"
    assert payload["details"][0]["reason"] == "iata_invalido"
    assert payload["details"][0]["normalized_payload"]["origin_iata"] == "AG"
