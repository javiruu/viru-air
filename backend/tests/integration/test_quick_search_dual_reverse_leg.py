"""Fase 8 — Backend audit: reverse leg, calendar hints with inverted IATA, 
and deep link with date_in for round-trip (ida/vuelta) support.

These tests confirm the backend is route-direction-agnostic and that the
frontend's strategy of inverting IATA for the return leg produces correct
results end-to-end.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFlight
from app.services.quick_search_execution import _CACHE
from tests.helpers import register_and_token


# ── Fake providers ────────────────────────────────────────────────────

class _ReverseLegProvider:
    """Returns flights for BOTH directions: AGP→DUB AND DUB→AGP."""

    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(
        self,
        origin: str,
        destination: str,
        travel_date: str,
        timeout_ms: int = 8000,
        **kwargs: object,
    ) -> list[ProviderFlight]:
        route = f"{origin}-{destination}"
        route_prices: dict[str, float] = {
            "AGP-DUB": 39.99,
            "DUB-AGP": 44.99,
        }
        price = route_prices.get(route)
        if price is None:
            return []
        return [
            ProviderFlight(
                price=price,
                currency="EUR",
                departure_time_local="08:40",
                captured_at=utc_now_naive(),
                source="fake-reverse-leg-provider",
            )
        ]


class _CalendarHintsInvertedProvider:
    """Returns flights for DUB→MAD, simulating an inverted calendar-hints
    request for the return leg."""

    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(
        self,
        origin: str,
        destination: str,
        travel_date: str,
        timeout_ms: int = 8000,
        **kwargs: object,
    ) -> list[ProviderFlight]:
        route = f"{origin}-{destination}"
        day = int(travel_date.split("-")[2])
        # Return-leg prices: DUB→MAD (inverted from the existing MAD→DUB test fixture)
        if route == "DUB-MAD" and day in {8, 12, 18}:
            return [
                ProviderFlight(
                    price={8: 70.0, 12: 130.0, 18: 200.0}[day],
                    currency="EUR",
                    departure_time_local="09:15",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-inverted-provider",
                )
            ]
        return []


# ── Reverse leg tests ─────────────────────────────────────────────────

def test_quick_search_reverse_leg_agp_to_dub(client: TestClient, monkeypatch) -> None:
    """Ida: AGP → DUB must return results."""
    fake_provider = _ReverseLegProvider()
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


def test_quick_search_reverse_leg_dub_to_agp(client: TestClient, monkeypatch) -> None:
    """Vuelta: DUB → AGP (inverted IATA) must also return results."""
    fake_provider = _ReverseLegProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    travel_date = str(date.today() + timedelta(days=28))
    response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "DUB", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "destination": {"seed_iata": "AGP", "include_nearby": False, "radius_km": 150, "max_candidates": 6},
            "travel": {"date": travel_date, "flex_before": 0, "flex_after": 0},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) >= 1
    first = payload["results"][0]
    assert first["origin"] == "DUB"
    assert first["destination"] == "AGP"
    assert first["travel_date"] == travel_date
    assert first["price_total"] == 44.99


def test_quick_search_reverse_leg_different_results(client: TestClient, monkeypatch) -> None:
    """Ida and vuelta should return different prices (different direction, different provider results)."""
    fake_provider = _ReverseLegProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    outbound_date = str(date.today() + timedelta(days=21))
    return_date = str(date.today() + timedelta(days=28))

    ida = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP"},
            "destination": {"seed_iata": "DUB"},
            "travel": {"date": outbound_date},
        },
    )
    vuelta = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "DUB"},
            "destination": {"seed_iata": "AGP"},
            "travel": {"date": return_date},
        },
    )

    assert ida.status_code == 200
    assert vuelta.status_code == 200

    ida_price = ida.json()["results"][0]["price_total"]
    vuelta_price = vuelta.json()["results"][0]["price_total"]

    # Different directions should yield different prices (not a generic round-trip)
    assert ida_price != vuelta_price
    assert ida_price == 39.99
    assert vuelta_price == 44.99


# ── Calendar hints with inverted IATA pair ────────────────────────────

def test_calendar_hints_inverted_iata_for_return_leg(client: TestClient, monkeypatch) -> None:
    """Simulate the frontend's return-leg calendar-hints request:
    DUB → MAD (inverted from the standard MAD → DUB)."""
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    fake_provider = _CalendarHintsInvertedProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    payload = {
        "origin_iata": "DUB",
        "destination_iata": "MAD",
        "month": "2030-06",
        "adults": 1,
    }

    response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["days"]) == 30
    assert data["meta"]["scope_mode"] == "iata"
    assert data["meta"]["cache_hit"] is False

    days_by_iso = {day["date"]: day for day in data["days"]}
    assert days_by_iso["2030-06-08"]["bucket"] == "low"
    assert days_by_iso["2030-06-08"]["min_price"] == 70.0
    assert days_by_iso["2030-06-12"]["bucket"] == "mid"
    assert days_by_iso["2030-06-12"]["min_price"] == 130.0
    assert days_by_iso["2030-06-18"]["bucket"] == "high"
    assert days_by_iso["2030-06-18"]["min_price"] == 200.0
    # Days without data
    assert days_by_iso["2030-06-01"]["bucket"] == "none"
    assert days_by_iso["2030-06-01"]["no_data_reason"] == "no_fare_data"


def test_calendar_hints_inverted_country_scope(client: TestClient, monkeypatch) -> None:
    """Inverted country-scope: DUB as origin pool, Spanish airports as destination."""
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    # We need a provider that returns something for country-scope pairs.
    # The _CalendarHintsInvertedProvider only handles DUB-MAD, but country-scope
    # will create pairs like DUB-MAD, DUB-BCN, DUB-AGP. We'll use a broader provider.
    class _CountryScopeInvertedProvider:
        def provider_ids(self) -> list[str]:
            return ["fake"]

        def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000, **kwargs: object):
            day = int(travel_date.split("-")[2])
            if origin == "DUB" and destination in {"MAD", "BCN", "AGP"} and day in {5, 10, 15}:
                return [
                    ProviderFlight(
                        price={"MAD": 70.0, "BCN": 85.0, "AGP": 95.0}[destination],
                        currency="EUR",
                        departure_time_local="09:00",
                        captured_at=utc_now_naive(),
                        source="country-scope-inverted-provider",
                    )
                ]
            return []

    fake_provider = _CountryScopeInvertedProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    payload = {
        "origin_iata": ["DUB"],
        "destination_iata": ["MAD", "BCN", "AGP"],
        "month": "2030-06",
        "adults": 1,
        "aggregation_mode": "min",
    }

    response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["meta"]["scope_mode"] == "country_mixed"
    # Verify the endpoint correctly handles inverted scope direction
    assert data["meta"]["ranked_airports"]["origin_count"] >= 1
    assert data["meta"]["ranked_airports"]["destination_count"] >= 1


# ── Deep link with date_in (round-trip) ───────────────────────────────

def test_deeplink_with_date_in_creates_round_trip_url(client: TestClient) -> None:
    """Deep link with date_in should produce a round-trip URL with isReturn=true."""
    travel_date = str(date.today() + timedelta(days=21))
    return_date = str(date.today() + timedelta(days=28))

    response = client.get(
        "/api/v1/search/deeplink",
        params={
            "origin_iata": "AGP",
            "destination_iata": "DUB",
            "date_out": travel_date,
            "date_in": return_date,
            "adults": 1,
            "teens": 0,
            "children": 0,
            "infants": 0,
            "locale": "es-es",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["origin_iata"] == "AGP"
    assert body["destination_iata"] == "DUB"
    assert body["date_out"] == travel_date
    assert body["date_in"] == return_date
    assert "ryanair.com" in body["url"]
    assert "isReturn=true" in body["url"]
    assert f"dateOut={travel_date}" in body["url"]
    assert f"dateIn={return_date}" in body["url"]


def test_deeplink_with_date_in_rejects_invalid_return_date(client: TestClient) -> None:
    """Deep link must reject return_date < outbound_date."""
    travel_date = str(date.today() + timedelta(days=28))
    return_date = str(date.today() + timedelta(days=21))  # BEFORE outbound

    response = client.get(
        "/api/v1/search/deeplink",
        params={
            "origin_iata": "AGP",
            "destination_iata": "DUB",
            "date_out": travel_date,
            "date_in": return_date,
            "adults": 1,
            "locale": "es-es",
        },
    )

    assert response.status_code >= 400
    error_body = response.json()
    assert "deeplink" in error_body.get("code", "").lower()


def test_deeplink_without_date_in_is_one_way(client: TestClient) -> None:
    """Deep link without date_in should be one-way (isReturn=false)."""
    travel_date = str(date.today() + timedelta(days=21))

    response = client.get(
        "/api/v1/search/deeplink",
        params={
            "origin_iata": "AGP",
            "destination_iata": "DUB",
            "date_out": travel_date,
            "adults": 1,
            "locale": "es-es",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["date_in"] is None
    assert "isReturn=false" in body["url"]
    assert "dateIn=" in body["url"]  # empty dateIn for one-way


# ── Save result with group_id for combination ─────────────────────────

def test_save_result_with_group_id(client: TestClient, monkeypatch) -> None:
    """Saving a result with group_id should succeed (used for dual combinations)."""
    token = register_and_token(client, email="save-group-id@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    class _SingleFlightProvider:
        def provider_ids(self) -> list[str]:
            return ["fake"]

        def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000, **kwargs: object):
            return [
                ProviderFlight(
                    price=49.99,
                    currency="EUR",
                    departure_time_local="08:00",
                    captured_at=utc_now_naive(),
                    source="group-id-provider",
                )
            ]

    fake_provider = _SingleFlightProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    travel_date = str(date.today() + timedelta(days=21))
    search_response = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP"},
            "destination": {"seed_iata": "DUB"},
            "travel": {"date": travel_date},
        },
        headers=headers,
    )
    assert search_response.status_code == 200

    result = search_response.json()["results"][0]
    group_id = "test-dual-group-001"

    save_response = client.post(
        "/api/v1/search/save-result",
        json={
            "origin_iata": result["origin"],
            "destination_iata": result["destination"],
            "travel_date": result["travel_date"],
            "price_total": result["price_total"],
            "group_id": group_id,
        },
        headers=headers,
    )

    assert save_response.status_code == 200
    save_body = save_response.json()
    assert save_body.get("created_or_existing") in ("created", "existing")


def test_save_result_reverse_leg_with_same_group_id(client: TestClient, monkeypatch) -> None:
    """Outbound and return legs saved with the same group_id should both succeed,
    creating a linked dual combination."""
    token = register_and_token(client, email="save-reverse-group@viru.dev")
    headers = {"Authorization": f"Bearer {token}"}

    class _DualSaveProvider:
        def provider_ids(self) -> list[str]:
            return ["fake"]

        def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000, **kwargs: object):
            return [
                ProviderFlight(
                    price=49.99 if origin == "AGP" else 54.99,
                    currency="EUR",
                    departure_time_local="08:00",
                    captured_at=utc_now_naive(),
                    source="dual-save-provider",
                )
            ]

    fake_provider = _DualSaveProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    outbound_date = str(date.today() + timedelta(days=21))
    return_date = str(date.today() + timedelta(days=28))
    group_id = "test-dual-group-002"

    # Outbound: AGP → DUB
    outbound_search = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "AGP"},
            "destination": {"seed_iata": "DUB"},
            "travel": {"date": outbound_date},
        },
        headers=headers,
    )
    assert outbound_search.status_code == 200
    outbound_result = outbound_search.json()["results"][0]

    outbound_save = client.post(
        "/api/v1/search/save-result",
        json={
            "origin_iata": outbound_result["origin"],
            "destination_iata": outbound_result["destination"],
            "travel_date": outbound_result["travel_date"],
            "price_total": outbound_result["price_total"],
            "group_id": group_id,
        },
        headers=headers,
    )
    assert outbound_save.status_code == 200

    # Return: DUB → AGP (inverted IATA)
    return_search = client.post(
        "/api/v1/search/quick",
        json={
            "origin": {"seed_iata": "DUB"},
            "destination": {"seed_iata": "AGP"},
            "travel": {"date": return_date},
        },
        headers=headers,
    )
    assert return_search.status_code == 200
    return_result = return_search.json()["results"][0]

    return_save = client.post(
        "/api/v1/search/save-result",
        json={
            "origin_iata": return_result["origin"],
            "destination_iata": return_result["destination"],
            "travel_date": return_result["travel_date"],
            "price_total": return_result["price_total"],
            "group_id": group_id,
        },
        headers=headers,
    )
    assert return_save.status_code == 200

    # Both entries share the same group_id
    assert outbound_save.json().get("created_or_existing") in ("created", "existing")
    assert return_save.json().get("created_or_existing") in ("created", "existing")
