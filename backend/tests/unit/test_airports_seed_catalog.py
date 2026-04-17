from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_airports_seeds_exposes_quick_search_catalog() -> None:
    response = client.get("/api/v1/airports/seeds")

    assert response.status_code == 200
    payload = response.json()

    assert payload["source"] == "catalog_master"
    assert payload["count"] == len(payload["items"])
    assert payload["count"] > 0

    items_by_iata = {item["iata"]: item for item in payload["items"]}
    assert "AGP" in items_by_iata
    assert "DUB" in items_by_iata
    assert "TSF" not in items_by_iata

    agp = items_by_iata["AGP"]
    assert agp["municipality"] == "Malaga"
    assert agp["country_code"] == "ES"
    assert agp["iso_region"] == "ES-AN"
