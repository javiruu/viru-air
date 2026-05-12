from fastapi.testclient import TestClient

import app.api.v1.airports as airports_api
from app.main import app


client = TestClient(app)


def test_airports_compatible_requires_one_side() -> None:
    response = client.get("/api/v1/airports/compatible", params={"travel_date": "2026-06-15"})
    assert response.status_code == 400
    payload = response.json()
    assert payload.get("code") == "missing_origin_or_destination"


def test_airports_compatible_rejects_both_sides() -> None:
    response = client.get(
        "/api/v1/airports/compatible",
        params={
            "travel_date": "2026-06-15",
            "origin_iata": "MAD",
            "destination_iata": "DUB",
        },
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload.get("code") == "provide_origin_or_destination_only"


def test_airports_compatible_returns_mocked_catalog(monkeypatch) -> None:
    monkeypatch.setattr(airports_api, "_compatible_from_iata", lambda iata: ["DUB", "CRL"] if iata == "MAD" else [])
    response = client.get(
        "/api/v1/airports/compatible",
        params={"travel_date": "2026-06-15", "origin_iata": "MAD"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["seed_iata"] == "MAD"
    assert payload["compatible_iata"] == ["DUB", "CRL"]
    assert payload["source"] == "airportroutes"


def test_airports_nearby_validates_radius_and_limit() -> None:
    low_radius = client.get("/api/v1/airports/nearby", params={"iata": "MAD", "radius_km": 5, "limit": 8})
    assert low_radius.status_code == 400
    assert low_radius.json().get("code") == "radius_invalido"

    high_limit = client.get("/api/v1/airports/nearby", params={"iata": "MAD", "radius_km": 150, "limit": 25})
    assert high_limit.status_code == 400
    assert high_limit.json().get("code") == "limit_invalido"
