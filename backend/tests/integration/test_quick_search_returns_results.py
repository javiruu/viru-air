from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from app.domain.schemas import FareComparisonProfile
from tests.helpers import register_and_token


class _FakeQuickSearchProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000, **kwargs: object) -> list[ProviderFlight]:
        if origin == "AGP" and destination == "DUB":
            return [
                ProviderFlight(
                    price=39.99,
                    currency="EUR",
                    departure_time_local="08:40",
                    captured_at=utc_now_naive(),
                    source="fake-quick-search-provider",
                    carrier_code="FR",
                    flight_number="FR1234",
                )
            ]
        return []


class _MalformedPriceQuickSearchProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000, **kwargs: object) -> list[ProviderFlight]:
        if origin == "AGP" and destination == "DUB":
            return [
                ProviderFlight(
                    price="not-a-price",
                    currency="EUR",
                    departure_time_local="08:40",
                    captured_at=utc_now_naive(),
                    source="malformed-provider",
                ),
                ProviderFlight(
                    price=39.99,
                    currency="EUR",
                    departure_time_local="09:40",
                    captured_at=utc_now_naive(),
                    source="fake-quick-search-provider",
                ),
            ]
        return []


def test_fare_comparison_profile_rejects_non_finite_amounts() -> None:
    with pytest.raises(ValidationError):
        FareComparisonProfile.model_validate(
            {
                "travelers": 1,
                "extras": [
                    {
                        "kind": "cabin_bag_10kg",
                        "selected": True,
                        "amount_per_person": 1e309,
                    }
                ],
            }
        )


def test_quick_search_valid_route_returns_at_least_one_result(client: TestClient, monkeypatch) -> None:
    fake_provider = _FakeQuickSearchProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    travel_date = str(date.today() + timedelta(days=21))
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["results"]) >= 1
    first = payload["results"][0]
    assert first["origin"] == "AGP"
    assert first["destination"] == "DUB"
    assert first["travel_date"] == travel_date
    assert first["price_total"] == 39.99
    assert first["source"] == "fake-quick-search-provider"
    assert first["legs"][0]["flight_num"] == "FR1234"
    assert first["legs"][0]["arr_ts"] is None


def test_quick_search_result_links_through_save_to_watchlist_live(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(search_api, "_build_request_provider", _FakeQuickSearchProvider)
    travel_date = str(date.today() + timedelta(days=22))
    search_response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP", "include_nearby": False},
            "destination": {"seed_iata": "DUB", "include_nearby": False},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
        },
    )
    assert search_response.status_code == 200
    result = search_response.json()["results"][0]
    result_leg = result["legs"][0]
    token = register_and_token(client, email="quick-to-live@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}
    fare_profile = {
        "travelers": 2,
        "extras": [
            {"kind": "cabin_bag_10kg", "selected": True, "amount_per_person": 18.0},
            {"kind": "insurance", "selected": True, "amount_per_person": 9.5},
            {"kind": "fast_track", "selected": False, "amount_per_person": None},
        ],
    }

    save_response = client.post(
        "/api/v1/search/save-result",
        headers=headers,
        json={
            "origin_iata": result["origin"],
            "destination_iata": result["destination"],
            "travel_date": result["travel_date"],
            "price_total": result["price_total"],
            "currency": result["currency"],
            "fare_profile": fare_profile,
            "legs": [
                {
                    "flight_number": result_leg["flight_num"],
                    "carrier_code": result_leg["carrier_code"],
                    "origin_iata": result_leg["origin_iata"],
                    "destination_iata": result_leg["destination_iata"],
                    "departure_at": result_leg["dep_ts"],
                    "arrival_at": result_leg["arr_ts"],
                }
            ],
        },
    )

    assert save_response.status_code == 200
    detail_response = client.get(
        f"/api/v1/watchlist/{save_response.json()['watch_id']}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["fare_profile"] == fare_profile
    live_response = client.get(
        f"/api/v1/watchlist/{save_response.json()['watch_id']}/live",
        headers=headers,
    )
    assert live_response.status_code == 200
    assert live_response.json()["legs"][0]["identity"]["flight_number"] == "FR1234"


def test_quick_search_skips_malformed_provider_prices(client: TestClient, monkeypatch) -> None:
    fake_provider = _MalformedPriceQuickSearchProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    travel_date = str(date.today() + timedelta(days=21))
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 1
    assert payload["results"][0]["price_total"] == 39.99
    assert payload["results"][0]["source"] == "fake-quick-search-provider"
