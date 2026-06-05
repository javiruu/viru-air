"""Unit tests for MakcorpsHotelProviderAdapter with response fixtures."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord
from app.hotels.makcorps_provider import MakcorpsHotelProviderAdapter


def _makcorps_city_fixture_payload() -> dict:
    """Simulates the /city endpoint response (flat comparison array)."""
    return {
        "hotels": [
            {
                "hotelId": "mk-001",
                "name": "Grand Hotel Ritz",
                "address": "Plaza de la Lealtad 5",
                "city": "Madrid",
                "country": "ES",
                "geocode": {"lat": 40.4153, "lng": -3.6925},
                "stars": 5,
                "comparison": [
                    {
                        "price": 245.00,
                        "tax": 24.50,
                        "room_type": "Deluxe King",
                        "meal": "Breakfast",
                    },
                    {
                        "price": 298.50,
                        "tax": 29.85,
                        "room_type": "Suite",
                        "meal": "Half Board",
                    },
                ],
            },
            {
                "hotelId": "mk-002",
                "name": "Hotel Costasol",
                "city": "Valencia",
                "country": "ES",
                "stars": 3,
                "comparison": [
                    {
                        "price": 89.00,
                        "tax": 8.90,
                    }
                ],
            },
        ]
    }


def _makcorps_hotel_fixture_payload() -> dict:
    """Simulates the /hotel endpoint response (numbered-key format)."""
    return {
        "comparison": [
            [
                {
                    "vendor1": "Expedia",
                    "price1": 376,
                    "Totalprice1": 376,
                    "tax1": 37.6,
                },
                {
                    "vendor2": "Booking.com",
                    "price2": 389,
                    "Totalprice2": 389,
                    "tax2": 38.9,
                },
                {
                    "vendor3": "Agoda",
                    "price3": 360,
                    "Totalprice3": 360,
                    "tax3": 36.0,
                },
            ]
        ]
    }


def _mock_session(status_code: int = 200, json_payload: dict | None = None) -> MagicMock:
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_payload or _makcorps_city_fixture_payload()

    def _raise_for_status():
        if status_code >= 400:
            http_error = requests.exceptions.HTTPError(
                f"{status_code} Error"
            )
            http_error.response = response
            raise http_error

    response.raise_for_status = _raise_for_status
    session.get.return_value = response
    return session


class TestMakcorpsProviderAdapter:
    def test_adapter_has_provider_id(self):
        with patch(
            "app.hotels.makcorps_provider._MAKCORPS_API_KEY", "test-key"
        ):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            assert adapter.provider_id == "makcorps"
            assert isinstance(adapter, HotelProviderAdapter)

    def test_is_disabled_without_api_key(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", ""):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            assert adapter.is_enabled() is False

    def test_is_enabled_with_api_key(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test-123"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            assert adapter.is_enabled() is True

    def test_fetch_hotels_parses_valid_city_response(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            result = adapter.fetch_hotels(city_id="test-city-123")

            assert len(result) == 2
            assert isinstance(result[0], ProviderHotelRecord)
            assert result[0].provider_hotel_id == "mk-001"
            assert result[0].raw_name == "Grand Hotel Ritz"
            assert result[0].city == "Madrid"
            assert result[0].country_code == "ES"
            assert result[0].latitude == 40.4153
            assert result[0].stars == 5
            assert len(result[0].rates) == 2
            assert result[0].rates[0].amount == 269.50  # 245 + 24.50 tax
            assert result[0].rates[0].currency == "EUR"
            assert result[0].rates[0].room_label == "Deluxe King"

            assert result[1].provider_hotel_id == "mk-002"
            assert result[1].city == "Valencia"
            assert len(result[1].rates) == 1

    def test_fetch_hotels_handles_empty_response(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload={"hotels": []})
            )
            result = adapter.fetch_hotels(city_id="test-city-123")
            assert result == []

    def test_fetch_hotels_rejects_malformed_top_level_payload(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=["bad-payload"])
            )
            result = adapter.fetch_hotels(city_id="test-city-123")
            assert result == []

    def test_fetch_hotels_handles_rates_without_dates(self):
        payload = {
            "hotels": [
                {
                    "hotelId": "mk-003",
                    "name": "No Rates Hotel",
                    "city": "Barcelona",
                    "country": "ES",
                    "comparison": [
                        {"price": 100, "tax": 10},
                    ],
                }
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=payload)
            )
            result = adapter.fetch_hotels(city_id="test-city-123")
            assert len(result) == 1
            assert result[0].rates[0].amount == 110.0

    def test_fetch_hotels_discards_invalid_amounts_and_currency(self):
        payload = {
            "hotels": [
                {
                    "hotelId": "mk-004",
                    "name": "Broken Rates Hotel",
                    "city": "Sevilla",
                    "country": "ES",
                    "comparison": [
                        {"price": 0, "tax": 0},
                        {"price": "oops", "tax": 10},
                    ],
                }
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=payload)
            )
            result = adapter.fetch_hotels(city_id="test-city-123")
            assert len(result) == 1
            assert result[0].provider_hotel_id == "mk-004"
            assert result[0].rates == []

    def test_fetch_hotels_raises_without_api_key(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", ""):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            with pytest.raises(ValueError, match="not enabled"):
                adapter.fetch_hotels(city_id="test-city-123")

    def test_fetch_hotels_raises_on_http_error(self):
        with patch(
            "app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"
        ):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(status_code=500)
            )
            with pytest.raises(ValueError, match="returned no data"):
                adapter.fetch_hotels(city_id="test-city-123")

    def test_fetch_hotels_raises_on_429(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(status_code=429)
            )
            with pytest.raises(ValueError, match="returned no data"):
                adapter.fetch_hotels(city_id="test-city-123")

    def test_fetch_hotels_raises_on_timeout(self):
        with patch(
            "app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"
        ):
            session = _mock_session()
            session.get.side_effect = requests.exceptions.Timeout("Timed out")
            adapter = MakcorpsHotelProviderAdapter(session=session)
            with pytest.raises(ValueError, match="returned no data"):
                adapter.fetch_hotels(city_id="test-city-123")

    def test_fetch_hotels_skips_items_missing_id(self):
        payload = {
            "hotels": [
                {"name": "No ID Hotel", "city": "Test", "country": "XX"},
                {
                    "hotelId": "mk-valid",
                    "name": "Valid Hotel",
                    "city": "Test",
                    "country": "XX",
                },
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=payload)
            )
            result = adapter.fetch_hotels(city_id="test-city-123")
            assert len(result) == 1
            assert result[0].provider_hotel_id == "mk-valid"

    def test_logs_never_expose_api_key(self, caplog: pytest.LogCaptureFixture):
        secret = "sk-secret-never-log"
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", secret):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(status_code=500)
            )
            with pytest.raises(ValueError):
                adapter.fetch_hotels(city_id="test-city-123")
        assert secret not in caplog.text

    def test_disabled_warning_never_exposes_api_key(self, caplog: pytest.LogCaptureFixture):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", ""):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            assert adapter.is_enabled() is False
        assert "MAKCORPS_API_KEY" in caplog.text

    # ── /hotel endpoint tests (numbered-key format) ──────────────────

    def test_fetch_hotel_rates_parses_numbered_key_format(self):
        """The real /hotel API returns [[{vendor1, price1, tax1, ...}, ...]]."""
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(
                    json_payload=_makcorps_hotel_fixture_payload()
                )
            )
            from datetime import date

            result = adapter.fetch_hotel_rates(
                "4719800",
                check_in=date(2026, 7, 1),
                check_out=date(2026, 7, 3),
                guests=2,
                currency="EUR",
            )
            assert len(result) == 3
            # Cheapest: vendor3 = 360 + 36 = 396
            amounts = sorted(r.amount for r in result)
            assert amounts[0] == pytest.approx(396.0)
            assert amounts[-1] == pytest.approx(427.9)  # vendor2: 389 + 38.9

    def test_fetch_hotel_rates_handles_currency_symbols(self):
        """price1 may be '€753' with currency symbol prefix."""
        payload = {
            "comparison": [
                [
                    {"vendor1": "TestOTA", "price1": "€753", "tax1": "€75.30"},
                    {"vendor2": "TestOTA2", "price2": "$820", "tax2": "$82.00"},
                ]
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=payload)
            )
            from datetime import date

            result = adapter.fetch_hotel_rates(
                "test-hotel",
                check_in=date(2026, 7, 1),
                check_out=date(2026, 7, 3),
            )
            assert len(result) == 2
            amounts = [r.amount for r in result]
            assert 828.30 in amounts  # 753 + 75.30
            assert 902.00 in amounts  # 820 + 82.00

    def test_fetch_hotel_rates_handles_empty_comparison(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload={"comparison": []})
            )
            from datetime import date

            result = adapter.fetch_hotel_rates(
                "test-hotel",
                check_in=date(2026, 7, 1),
                check_out=date(2026, 7, 3),
            )
            assert result == []

    def test_fetch_hotel_rates_sparse_payload(self):
        """Some vendor objects may be empty dicts."""
        payload = {
            "comparison": [
                [
                    {},  # empty vendor slot
                    {"vendor2": "ActiveOTA", "price2": 500, "tax2": 50},
                ]
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=payload)
            )
            from datetime import date

            result = adapter.fetch_hotel_rates(
                "test-hotel",
                check_in=date(2026, 7, 1),
                check_out=date(2026, 7, 3),
            )
            assert len(result) == 1
            assert result[0].amount == 550.0

    # ── mapping tests ────────────────────────────────────────────────

    def test_resolve_city_id_finds_geo_type(self):
        mapping_payload = [
            {"type": "HOTEL", "document_id": "hotel-123", "name": "Hotel Madrid"},
            {"type": "GEO", "document_id": "187514", "name": "Madrid"},
        ]
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=mapping_payload)
            )
            result = adapter.resolve_city_id("Madrid")
            assert result == "187514"

    def test_resolve_city_id_falls_back_to_any_type(self):
        mapping_payload = [
            {"type": "HOTEL", "document_id": "hotel-456", "name": "Barcelona Hotel"},
        ]
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=mapping_payload)
            )
            result = adapter.resolve_city_id("Barcelona")
            assert result == "hotel-456"

    def test_resolve_city_id_returns_none_for_empty(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(
                session=_mock_session(json_payload=[])
            )
            result = adapter.resolve_city_id("Nowhere")
            assert result is None
