import datetime as dt

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

import app.api.v1.search as search_api
from app.core.time import utc_now_naive
from app.domain.entities import ProviderFetchResult, ProviderFlight
from app.services.calendar_price_intelligence import CalendarStoredPrice
from app.services.quick_search_execution import _CACHE


class _CalendarHintsProvider:
    def __init__(self) -> None:
        self.calls = 0

    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        self.calls += 1
        day = int(travel_date.split("-")[2])
        route = f"{origin}-{destination}"
        route_prices: dict[str, dict[int, float]] = {
            "MAD-DUB": {5: 60.0, 10: 120.0, 15: 210.0},
            "BCN-DUB": {5: 80.0, 10: 110.0, 15: 160.0},
            "AGP-DUB": {5: 95.0, 10: 100.0, 15: 150.0},
        }
        route_day_prices = route_prices.get(route, {})
        if day in route_day_prices:
            return [
                ProviderFlight(
                    price=route_day_prices[day],
                    currency="EUR",
                    departure_time_local="08:10",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-provider",
                )
            ]
        return []


class _MalformedCalendarHintFlight:
    price = "not-a-price"
    currency = "EUR"


class _CalendarHintsInvalidPriceProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        return [_MalformedCalendarHintFlight()]


class _ContextualCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        prices = {5: 80.0, 10: 90.0, 15: 100.0, 20: 110.0, 25: 130.0}
        price = prices.get(int(travel_date.split("-")[2]))
        if price is None:
            return []
        return [
            ProviderFlight(
                price=price,
                currency="EUR",
                departure_time_local="08:10",
                captured_at=utc_now_naive(),
                source="calendar-hints-provider",
            )
        ]


class _AllDaysCalendarHintsProvider:
    def __init__(self) -> None:
        self.calls = 0

    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        self.calls += 1
        return [
            ProviderFlight(
                price=100.0,
                currency="EUR",
                departure_time_local="08:10",
                captured_at=utc_now_naive(),
                source="calendar-hints-provider",
            )
        ]


class _ObservedDaysCalendarHintsProvider:
    def __init__(self) -> None:
        self.travel_dates: list[str] = []

    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        self.travel_dates.append(travel_date)
        return []


class _MixedCurrencyCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        if travel_date != "2030-06-05":
            return []
        return [
            ProviderFlight(
                price=100.0,
                currency="USD",
                departure_time_local="08:10",
                captured_at=utc_now_naive(),
                source="calendar-hints-provider",
            ),
            ProviderFlight(
                price=95.0,
                currency="EUR",
                departure_time_local="12:10",
                captured_at=utc_now_naive(),
                source="calendar-hints-provider",
            ),
        ]


class _UnsupportedCurrencyCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        return [
            ProviderFlight(
                price=50.0,
                currency="ZZZ",
                departure_time_local="08:10",
                captured_at=utc_now_naive(),
                source="calendar-hints-provider",
            )
        ]


class _MixedQualityCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        day = int(travel_date.split("-")[2])
        if day == 5:
            return [
                ProviderFlight(
                    price=50.0,
                    currency="ZZZ",
                    departure_time_local="08:10",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-provider",
                )
            ]
        if day == 6:
            return ProviderFetchResult(flights=[], warnings=["provider_timeout_parcial"])
        return []


class _PartialPriceCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        if travel_date != "2030-06-05":
            return []
        if origin == "MAD":
            return [
                ProviderFlight(
                    price=80.0,
                    currency="EUR",
                    departure_time_local="08:10",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-provider",
                )
            ]
        return ProviderFetchResult(flights=[], warnings=["provider_timeout_parcial"])


class _PartialReferenceCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        day = int(travel_date.split("-")[2])
        if day not in {1, 2, 3, 4, 5}:
            return []
        if origin == "MAD":
            return [
                ProviderFlight(
                    price=float(day * 10),
                    currency="EUR",
                    departure_time_local="08:10",
                    captured_at=utc_now_naive(),
                    source="calendar-hints-provider",
                )
            ]
        return ProviderFetchResult(flights=[], warnings=["provider_timeout_parcial"])


class _CoverageRescueCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        if origin != "VLC" or destination != "DUB" or travel_date != "2030-06-02":
            return []
        return [
            ProviderFlight(
                price=70.0,
                currency="EUR",
                departure_time_local="08:10",
                captured_at=utc_now_naive(),
                source="calendar-hints-provider",
            )
        ]


class _TimeoutCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        raise TimeoutError("provider timeout")


class _MismatchedTravelDateCalendarHintsProvider:
    def provider_ids(self) -> list[str]:
        return ["fake"]

    def get_flights(self, origin: str, destination: str, travel_date: str, timeout_ms: int = 8000):
        return [
            ProviderFlight(
                price=50.0,
                currency="EUR",
                departure_time_local="08:10",
                captured_at=utc_now_naive(),
                travel_date="2030-06-30",
                source="calendar-hints-provider",
            )
        ]


def test_quick_search_calendar_hints_returns_month_with_buckets_and_cache(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    fake_provider = _CalendarHintsProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "month": "2030-06",
        "adults": 1,
    }

    response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 30
    assert data["meta"]["cache_hit"] is False
    assert data["meta"]["cache_ttl_sec"] == 600
    assert data["meta"]["partial"] is False
    assert data["meta"]["scope_mode"] == "iata"
    assert data["meta"]["aggregation_mode"] == "min"
    assert data["meta"]["bucket_mode"] == "contextual"
    assert data["meta"]["guideline_thresholds_effective"] is None

    days_by_iso = {day["date"]: day for day in data["days"]}
    assert days_by_iso["2030-06-05"]["bucket"] == "none"
    assert days_by_iso["2030-06-10"]["bucket"] == "none"
    assert days_by_iso["2030-06-15"]["bucket"] == "none"
    assert days_by_iso["2030-06-05"]["data_quality"] == "available"
    assert days_by_iso["2030-06-05"]["no_data_reason"] == "insufficient_reference"
    assert days_by_iso["2030-06-20"]["bucket"] == "none"
    assert days_by_iso["2030-06-20"]["no_data_reason"] == "no_fare_data"

    calls_after_first_request = fake_provider.calls
    assert calls_after_first_request > 0

    second_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["meta"]["cache_hit"] is True
    assert fake_provider.calls == calls_after_first_request


def test_quick_search_calendar_hints_country_scope_supports_aggregation_modes(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    fake_provider = _CalendarHintsProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    base_payload = {
        "origin_iata": ["MAD", "BCN", "AGP"],
        "destination_iata": "DUB",
        "month": "2030-06",
        "adults": 1,
    }

    min_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "min"},
    )
    assert min_response.status_code == 200
    min_data = min_response.json()
    assert min_data["meta"]["cache_hit"] is False
    assert min_data["meta"]["scope_mode"] == "country_mixed"
    assert min_data["meta"]["aggregation_mode"] == "min"
    assert min_data["meta"]["ranked_routes_count"] >= 1
    assert min_data["meta"]["ranked_airports"]["origin_count"] >= 1
    min_days_by_iso = {day["date"]: day for day in min_data["days"]}
    assert min_days_by_iso["2030-06-10"]["min_price"] == 100.0

    min_cached_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "min"},
    )
    assert min_cached_response.status_code == 200
    assert min_cached_response.json()["meta"]["cache_hit"] is True

    median_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "median"},
    )
    assert median_response.status_code == 200
    median_data = median_response.json()
    assert median_data["meta"]["cache_hit"] is False
    assert median_data["meta"]["scope_mode"] == "country_mixed"
    assert median_data["meta"]["aggregation_mode"] == "median"
    median_days_by_iso = {day["date"]: day for day in median_data["days"]}
    assert median_days_by_iso["2030-06-10"]["min_price"] == 110.0

    fixed_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "aggregation_mode": "fixed_route"},
    )
    assert fixed_response.status_code == 200
    fixed_data = fixed_response.json()
    assert fixed_data["meta"]["scope_mode"] == "country_mixed"
    assert fixed_data["meta"]["aggregation_mode"] == "fixed_route"
    fixed_days_by_iso = {day["date"]: day for day in fixed_data["days"]}
    assert fixed_days_by_iso["2030-06-10"]["min_price"] == 100.0

    country_country_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            "origin_iata": ["MAD", "BCN"],
            "destination_iata": ["DUB", "AGP"],
            "month": "2030-06",
            "adults": 1,
            "aggregation_mode": "min",
        },
    )
    assert country_country_response.status_code == 200
    country_country_data = country_country_response.json()
    assert country_country_data["meta"]["scope_mode"] == "country_country"


def test_quick_search_calendar_hints_supports_guideline_bucket_mode(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    fake_provider = _CalendarHintsProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    base_payload = {
        "origin_iata": "MAD",
        "destination_iata": "DUB",
        "month": "2030-06",
        "adults": 1,
    }

    terciles_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "bucket_mode": "monthly_terciles"},
    )
    assert terciles_response.status_code == 200
    terciles_data = terciles_response.json()
    terciles_days_by_iso = {day["date"]: day for day in terciles_data["days"]}
    assert terciles_days_by_iso["2030-06-15"]["bucket"] == "high"

    guidelines_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            **base_payload,
            "bucket_mode": "guidelines",
            "guideline_thresholds": {
                "low_max": 100,
                "mid_max": 220,
                "currency": "EUR",
            },
        },
    )
    assert guidelines_response.status_code == 200
    guidelines_data = guidelines_response.json()
    guidelines_days_by_iso = {day["date"]: day for day in guidelines_data["days"]}
    assert guidelines_days_by_iso["2030-06-15"]["bucket"] == "mid"
    assert guidelines_data["meta"]["bucket_mode"] == "guidelines"
    assert guidelines_data["meta"]["guideline_thresholds_effective"] == {
        "low_max": 100.0,
        "mid_max": 220.0,
        "currency": "EUR",
    }

    usd_guidelines_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            **base_payload,
            "currency": "USD",
            "bucket_mode": "guidelines",
            "guideline_thresholds": {
                "low_max": 100,
                "mid_max": 220,
                "currency": "EUR",
            },
        },
    )
    assert usd_guidelines_response.status_code == 200
    assert usd_guidelines_response.json()["meta"]["guideline_thresholds_effective"] == {
        "low_max": 107.53,
        "mid_max": 236.56,
        "currency": "USD",
    }

    usd_default_guidelines_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={**base_payload, "currency": "USD", "bucket_mode": "guidelines"},
    )
    assert usd_default_guidelines_response.status_code == 200
    assert usd_default_guidelines_response.json()["meta"]["guideline_thresholds_effective"] == {
        "low_max": 96.77,
        "mid_max": 161.29,
        "currency": "USD",
    }


def test_quick_search_calendar_hints_skips_invalid_provider_prices(client: TestClient, monkeypatch) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    fake_provider = _CalendarHintsInvalidPriceProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: fake_provider)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "month": "2030-06",
            "adults": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 30
    assert all(day["min_price"] is None for day in data["days"])


def test_quick_search_calendar_hints_uses_contextual_reference_when_the_sample_is_sufficient(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _ContextualCalendarHintsProvider)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"},
    )

    assert response.status_code == 200
    days_by_iso = {day["date"]: day for day in response.json()["days"]}
    assert days_by_iso["2030-06-05"]["bucket"] == "low"
    assert days_by_iso["2030-06-15"]["bucket"] == "mid"
    assert days_by_iso["2030-06-25"]["bucket"] == "high"
    assert response.json()["meta"]["coverage"]["days_priced"] == 5
    assert response.json()["meta"]["quality"]["classification_without_reference_count"] == 0


def test_quick_search_calendar_hints_normalizes_currencies_before_choosing_the_daily_price(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _MixedCurrencyCalendarHintsProvider)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "month": "2030-06",
            "currency": "EUR",
        },
    )

    assert response.status_code == 200
    days_by_iso = {day["date"]: day for day in response.json()["days"]}
    assert days_by_iso["2030-06-05"]["min_price"] == 93.0


def test_quick_search_calendar_hints_exposes_incompatible_currency_and_provider_timeout(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _UnsupportedCurrencyCalendarHintsProvider)

    currency_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"},
    )
    assert currency_response.status_code == 200
    assert currency_response.json()["days"][0]["no_data_reason"] == "incompatible_currency"

    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _TimeoutCalendarHintsProvider)
    timeout_response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-07"},
    )

    assert timeout_response.status_code == 200
    assert timeout_response.json()["days"][0]["no_data_reason"] == "provider_timeout"


def test_quick_search_calendar_hints_keeps_absence_causes_bound_to_the_affected_day(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _MixedQualityCalendarHintsProvider)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"},
    )

    assert response.status_code == 200
    days_by_iso = {day["date"]: day for day in response.json()["days"]}
    assert days_by_iso["2030-06-05"]["no_data_reason"] == "incompatible_currency"
    assert days_by_iso["2030-06-06"]["no_data_reason"] == "provider_timeout"
    assert days_by_iso["2030-06-07"]["no_data_reason"] == "no_fare_data"


def test_quick_search_calendar_hints_preserves_per_day_partial_quality_when_reused(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _PartialPriceCalendarHintsProvider)
    payload = {"origin_iata": ["MAD", "BCN"], "destination_iata": "DUB", "month": "2030-06"}

    first_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert first_response.status_code == 200
    first_days = {day["date"]: day for day in first_response.json()["days"]}
    assert first_days["2030-06-05"]["data_quality"] == "partial"

    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _TimeoutCalendarHintsProvider)
    reused_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)

    assert reused_response.status_code == 200
    reused_days = {day["date"]: day for day in reused_response.json()["days"]}
    assert reused_days["2030-06-05"]["data_quality"] == "partial"


def test_quick_search_calendar_hints_does_not_classify_from_partial_observations(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _PartialReferenceCalendarHintsProvider)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": ["MAD", "BCN"], "destination_iata": "DUB", "month": "2030-06"},
    )

    assert response.status_code == 200
    days_by_iso = {day["date"]: day for day in response.json()["days"]}
    assert days_by_iso["2030-06-01"]["data_quality"] == "partial"
    assert days_by_iso["2030-06-01"]["bucket"] == "none"
    assert days_by_iso["2030-06-01"]["reference_sample_size"] == 0


def test_quick_search_calendar_hints_uses_reserved_routes_to_rescue_uncovered_country_days(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _CoverageRescueCalendarHintsProvider)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            "origin_iata": ["AGP", "BCN", "IBZ", "LPA", "MAD", "PMI", "SVQ", "VLC"],
            "destination_iata": "DUB",
            "month": "2030-06",
        },
    )

    assert response.status_code == 200
    data = response.json()
    days_by_iso = {day["date"]: day for day in data["days"]}
    assert days_by_iso["2030-06-02"]["min_price"] == 70.0
    assert data["meta"]["ranked_routes_count"] == 8
    assert data["meta"]["coverage"]["days_priced"] == 1


def test_quick_search_calendar_hints_discards_flights_for_another_travel_day(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _MismatchedTravelDateCalendarHintsProvider)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["days"][0]["min_price"] is None
    assert data["meta"]["quality"]["travel_date_mismatch_count"] == 29


def test_quick_search_calendar_hints_reuses_fresh_observations_before_calling_the_provider(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _AllDaysCalendarHintsProvider)
    payload = {"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"}
    first_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert first_response.status_code == 200

    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _TimeoutCalendarHintsProvider)
    reused_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)

    assert reused_response.status_code == 200
    reused_data = reused_response.json()
    reused_days_by_iso = {day["date"]: day for day in reused_data["days"]}
    assert reused_days_by_iso["2030-06-05"]["min_price"] == 100.0
    assert reused_days_by_iso["2030-06-05"]["data_quality"] == "available"
    assert reused_data["meta"]["execution"]["provider_calls"] == 0


def test_quick_search_calendar_hints_skips_country_anchor_when_fresh_observations_cover_the_month(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    provider = _AllDaysCalendarHintsProvider()
    monkeypatch.setattr(search_api, "_build_request_provider", lambda: provider)
    payload = {"origin_iata": ["IBZ", "LPA"], "destination_iata": "DUB", "month": "2030-06"}

    first_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert first_response.status_code == 200
    first_call_count = provider.calls
    assert first_call_count > 0

    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    reused_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)

    assert reused_response.status_code == 200
    assert provider.calls == first_call_count
    assert reused_response.json()["meta"]["execution"]["provider_calls"] == 0


def test_quick_search_calendar_hints_anchors_only_days_missing_from_fresh_observations(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()

    provider = _ObservedDaysCalendarHintsProvider()
    now = utc_now_naive()
    missing_day = dt.date(2030, 6, 2)

    def load_reused_days(*, query_fingerprints: dict[dt.date, str]) -> dict[dt.date, CalendarStoredPrice]:
        return {
            day: CalendarStoredPrice(
                price=100.0,
                observed_at=now,
                expires_at=now + dt.timedelta(hours=1),
                freshness_status="fresh",
                coverage_status="available",
            )
            for day in query_fingerprints
            if day != missing_day
        }

    monkeypatch.setattr(search_api, "_build_request_provider", lambda: provider)
    monkeypatch.setattr(search_api, "load_latest_calendar_days", lambda _db, *, query_fingerprints: load_reused_days(query_fingerprints=query_fingerprints))
    monkeypatch.setattr(search_api, "load_fresh_calendar_reference", lambda _db, *, reference_fingerprint, now: [])
    monkeypatch.setattr(search_api, "record_calendar_prices", lambda *args, **kwargs: None)

    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": ["IBZ", "LPA"], "destination_iata": "DUB", "month": "2030-06"},
    )

    assert response.status_code == 200
    assert provider.travel_dates
    assert set(provider.travel_dates) == {missing_day.isoformat()}


def test_quick_search_calendar_hints_does_not_double_count_reused_reference_days(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _CalendarHintsProvider)
    payload = {"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"}
    first_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)
    assert first_response.status_code == 200

    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _TimeoutCalendarHintsProvider)
    reused_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)

    assert reused_response.status_code == 200
    days_by_iso = {day["date"]: day for day in reused_response.json()["days"]}
    assert days_by_iso["2030-06-05"]["bucket"] == "none"
    assert days_by_iso["2030-06-05"]["no_data_reason"] == "insufficient_reference"
    assert days_by_iso["2030-06-05"]["reference_sample_size"] == 3


def test_quick_search_calendar_hints_marks_expired_prices_as_stale_after_provider_timeout(
    client: TestClient,
    monkeypatch,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    now = utc_now_naive()
    monkeypatch.setattr(search_api, "_build_request_provider", _TimeoutCalendarHintsProvider)
    monkeypatch.setattr(
        search_api,
        "load_latest_calendar_days",
        lambda _db, *, query_fingerprints: {
            dt.date(2030, 6, 5): CalendarStoredPrice(
                price=60.0,
                observed_at=now - dt.timedelta(days=2),
                expires_at=now - dt.timedelta(days=1),
                freshness_status="fresh",
                coverage_status="available",
            )
        },
    )
    payload = {"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"}
    stale_response = client.post("/api/v1/search/quick/calendar-hints", json=payload)

    assert stale_response.status_code == 200
    days_by_iso = {day["date"]: day for day in stale_response.json()["days"]}
    assert days_by_iso["2030-06-05"] == {
        "date": "2030-06-05",
        "min_price": 60.0,
        "bucket": "none",
        "data_quality": "stale",
        "no_data_reason": "stale_reference",
        "reference_sample_size": 0,
    }


@pytest.mark.parametrize("error_type", [OperationalError, ProgrammingError])
def test_quick_search_calendar_hints_degrades_safely_before_the_observation_migration(
    client: TestClient,
    monkeypatch,
    error_type,
) -> None:
    _CACHE.clear()
    with search_api._CALENDAR_HINTS_CACHE_LOCK:
        search_api._CALENDAR_HINTS_CACHE.clear()
    monkeypatch.setattr(search_api, "_build_request_provider", _ContextualCalendarHintsProvider)

    def unavailable_reference(*args, **kwargs):
        raise error_type("SELECT calendar_price_observation", {}, RuntimeError("missing relation"))

    monkeypatch.setattr(search_api, "load_fresh_calendar_reference", unavailable_reference)
    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={"origin_iata": "MAD", "destination_iata": "DUB", "month": "2030-06"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["calendar_observations_available"] is False


def test_quick_search_calendar_hints_rejects_unimplemented_cabin_values(client: TestClient) -> None:
    response = client.post(
        "/api/v1/search/quick/calendar-hints",
        json={
            "origin_iata": "MAD",
            "destination_iata": "DUB",
            "month": "2030-06",
            "cabin": "business",
        },
    )

    assert response.status_code == 422
