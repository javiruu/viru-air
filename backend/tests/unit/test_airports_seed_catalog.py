from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_airports_seeds_exposes_quick_search_catalog() -> None:
    response = client.get("/api/v1/airports/seeds")

    assert response.status_code == 200
    payload = response.json()

    assert payload["source"] == "catalog_master"
    assert payload["count"] == len(payload["items"])
    assert payload["total"] == payload["count"]
    assert payload["count"] > 0

    items_by_iata = {item["iata"]: item for item in payload["items"]}
    assert "AGP" in items_by_iata
    assert "DUB" in items_by_iata
    assert "TSF" not in items_by_iata

    agp = items_by_iata["AGP"]
    assert agp["municipality"] == "Malaga"
    assert agp["country_code"] == "ES"
    assert agp["iso_region"] == "ES-AN"


def test_airports_seeds_supports_query_and_pagination() -> None:
    response = client.get("/api/v1/airports/seeds", params={"q": "dub", "limit": 5, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] <= 5
    assert payload["total"] >= payload["count"]
    assert payload["source"] == "catalog_master"
    assert any(item["iata"] == "DUB" for item in payload["items"])


def test_airports_seeds_supports_country_filter() -> None:
    response = client.get("/api/v1/airports/seeds", params={"country_code": "ES", "limit": 200})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] > 0
    assert all(item["country_code"] == "ES" for item in payload["items"])


def test_airports_countries_returns_country_counts() -> None:
    response = client.get("/api/v1/airports/countries")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "catalog_master"
    assert payload["count"] == len(payload["items"])
    assert payload["count"] > 0
    assert any(item["code"] == "ES" and item["airport_count"] > 0 for item in payload["items"])
