from __future__ import annotations

from fastapi.testclient import TestClient

from app.infrastructure.db.models import HotelProperty
from app.infrastructure.db.session import get_db
from app.main import app
from tests.helpers import register_and_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _open_overridden_db():
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    return db, generator


def test_hotels_search_matches_city_without_accents(client: TestClient) -> None:
    token = register_and_token(client, email="hotels-search-city-accents@viru.dev")
    headers = _auth(token)

    db, generator = _open_overridden_db()
    try:
        db.add_all(
            [
                HotelProperty(
                    canonical_name="Hotel Malaga Centro",
                    normalized_name="hotel malaga centro",
                    city="Málaga",
                    normalized_city="malaga",
                    country_code="ES",
                    stars=4,
                ),
                HotelProperty(
                    canonical_name="Hotel Cordoba Ribera",
                    normalized_name="hotel cordoba ribera",
                    city="Córdoba",
                    normalized_city="cordoba",
                    country_code="ES",
                    stars=4,
                ),
            ]
        )
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    malaga = client.get("/api/v1/hotels/search", params={"city": "Malaga"}, headers=headers)
    assert malaga.status_code == 200
    assert [item["canonical_name"] for item in malaga.json()] == ["Hotel Malaga Centro"]

    cordoba = client.get("/api/v1/hotels/search", params={"city": "cOrdObA"}, headers=headers)
    assert cordoba.status_code == 200
    assert [item["canonical_name"] for item in cordoba.json()] == ["Hotel Cordoba Ribera"]
