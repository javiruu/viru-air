"""Unit tests for MakcorpsHotelProviderAdapter with response fixtures."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord
from app.hotels.makcorps_provider import MakcorpsHotelProviderAdapter


def _makcorps_fixture_payload() -> dict:
    return {
        "data": [
            {
                "id": "mk-001",
                "name": "Grand Hotel Ritz",
                "address": "Plaza de la Lealtad 5",
                "city": "Madrid",
                "country_code": "ES",
                "latitude": 40.4153,
                "longitude": -3.6925,
                "stars": 5,
                "rates": [
                    {
                        "check_in": "2026-07-01",
                        "check_out": "2026-07-03",
                        "amount": 245.00,
                        "currency": "EUR",
                        "guests": 2,
                        "room_label": "Deluxe King",
                        "meal_plan": "Breakfast",
                        "cancellation_policy": "Free cancellation 24h",
                    },
                    {
                        "check_in": "2026-07-01",
                        "check_out": "2026-07-03",
                        "amount": 298.50,
                        "currency": "EUR",
                        "guests": 2,
                        "room_label": "Suite",
                        "meal_plan": "Half Board",
                    },
                ],
            },
            {
                "id": "mk-002",
                "name": "Hotel Costasol",
                "city": "Valencia",
                "country_code": "ES",
                "stars": 3,
                "rates": [
                    {
                        "check_in": "2026-08-15",
                        "check_out": "2026-08-18",
                        "amount": 89.00,
                        "currency": "EUR",
                    }
                ],
            },
        ]
    }


def _mock_session(status_code: int = 200, json_payload: dict | None = None) -> MagicMock:
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_payload or _makcorps_fixture_payload()
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Error", response=response
        )
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

    def test_fetch_hotels_parses_valid_response(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            result = adapter.fetch_hotels()

            assert len(result) == 2
            assert isinstance(result[0], ProviderHotelRecord)
            assert result[0].provider_hotel_id == "mk-001"
            assert result[0].raw_name == "Grand Hotel Ritz"
            assert result[0].city == "Madrid"
            assert result[0].country_code == "ES"
            assert result[0].latitude == 40.4153
            assert result[0].stars == 5
            assert len(result[0].rates) == 2
            assert result[0].rates[0].amount == 245.00
            assert result[0].rates[0].currency == "EUR"
            assert result[0].rates[0].room_label == "Deluxe King"

            assert result[1].provider_hotel_id == "mk-002"
            assert result[1].city == "Valencia"
            assert len(result[1].rates) == 1

    def test_fetch_hotels_handles_empty_response(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(json_payload={"data": []}))
            result = adapter.fetch_hotels()
            assert result == []

    def test_fetch_hotels_rejects_malformed_top_level_payload(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(json_payload=["bad-payload"]))
            with pytest.raises(ValueError, match="payload is invalid"):
                adapter.fetch_hotels()

    def test_fetch_hotels_handles_rates_without_dates(self):
        payload = {
            "data": [
                {
                    "id": "mk-003",
                    "name": "No Rates Hotel",
                    "city": "Barcelona",
                    "country_code": "ES",
                    "rates": [
                        {"amount": 100, "currency": "EUR"},
                    ],
                }
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(json_payload=payload))
            result = adapter.fetch_hotels()
            assert len(result) == 1
            assert len(result[0].rates) == 0

    def test_fetch_hotels_discards_invalid_amounts_and_currency(self):
        payload = {
            "data": [
                {
                    "id": "mk-004",
                    "name": "Broken Rates Hotel",
                    "city": "Sevilla",
                    "country_code": "ES",
                    "rates": [
                        {
                            "check_in": "2026-07-01",
                            "check_out": "2026-07-03",
                            "amount": 0,
                            "currency": "EUR",
                        },
                        {
                            "check_in": "2026-07-01",
                            "check_out": "2026-07-03",
                            "amount": "oops",
                            "currency": "EUR",
                        },
                        {
                            "check_in": "2026-07-01",
                            "check_out": "2026-07-03",
                            "amount": 120,
                            "currency": "EURO",
                        },
                    ],
                }
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(json_payload=payload))
            result = adapter.fetch_hotels()
            assert len(result) == 1
            assert result[0].provider_hotel_id == "mk-004"
            assert result[0].rates == []

    def test_fetch_hotels_raises_without_api_key(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", ""):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            with pytest.raises(ValueError, match="not enabled"):
                adapter.fetch_hotels()

    def test_fetch_hotels_raises_on_http_error(self):
        with patch(
            "app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"
        ):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(status_code=500))
            with pytest.raises(ValueError, match="status 500"):
                adapter.fetch_hotels()

    def test_fetch_hotels_raises_on_429(self):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(status_code=429))
            with pytest.raises(ValueError, match="status 429"):
                adapter.fetch_hotels()

    def test_fetch_hotels_raises_on_timeout(self):
        with patch(
            "app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"
        ):
            session = _mock_session()
            session.get.side_effect = requests.exceptions.Timeout("Timed out")
            adapter = MakcorpsHotelProviderAdapter(session=session)
            with pytest.raises(ValueError, match="timed out"):
                adapter.fetch_hotels()

    def test_fetch_hotels_skips_items_missing_id(self):
        payload = {
            "data": [
                {"name": "No ID Hotel", "city": "Test", "country_code": "XX"},
                {"id": "mk-valid", "name": "Valid Hotel", "city": "Test", "country_code": "XX"},
            ]
        }
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", "sk-test"):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(json_payload=payload))
            result = adapter.fetch_hotels()
            assert len(result) == 1
            assert result[0].provider_hotel_id == "mk-valid"

    def test_logs_never_expose_api_key(self, caplog: pytest.LogCaptureFixture):
        secret = "sk-secret-never-log"
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", secret):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session(status_code=500))
            with pytest.raises(ValueError):
                adapter.fetch_hotels()
        assert secret not in caplog.text

    def test_disabled_warning_never_exposes_bearer_value(self, caplog: pytest.LogCaptureFixture):
        with patch("app.hotels.makcorps_provider._MAKCORPS_API_KEY", ""):
            adapter = MakcorpsHotelProviderAdapter(session=_mock_session())
            assert adapter.is_enabled() is False
        assert "MAKCORPS_API_KEY" in caplog.text
        assert "Bearer" not in caplog.text
