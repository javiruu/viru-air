from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.hotels.mock_provider import MockHotelProviderAdapter


def test_mock_provider_trims_strings_and_normalizes_country_and_currency(tmp_path: Path) -> None:
    fixture = {
        "hotels": [
            {
                "provider_hotel_id": " mock-001 ",
                "name": " Hotel Sol Madrid ",
                "address": " Calle Sol 1 ",
                "city": " Madrid ",
                "country_code": " es ",
                "rates": [
                    {
                        "check_in": "2026-07-10",
                        "check_out": "2026-07-12",
                        "amount": 180,
                        "currency": " eur ",
                    }
                ],
            }
        ]
    }
    fixture_path = tmp_path / "mock_hotels_trimmed.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    records = MockHotelProviderAdapter(str(fixture_path)).fetch_hotels()

    assert len(records) == 1
    record = records[0]
    assert record.provider_hotel_id == "mock-001"
    assert record.raw_name == "Hotel Sol Madrid"
    assert record.raw_address == "Calle Sol 1"
    assert record.city == "Madrid"
    assert record.country_code == "ES"
    assert record.rates[0].currency == "EUR"


def test_mock_provider_rejects_invalid_country_code(tmp_path: Path) -> None:
    fixture = {
        "hotels": [
            {
                "provider_hotel_id": "mock-bad-country",
                "name": "Hotel Error",
                "address": "Calle Falsa 1",
                "city": "Madrid",
                "country_code": "ESP",
                "rates": [],
            }
        ]
    }
    fixture_path = tmp_path / "mock_hotels_invalid_country.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid country_code"):
        MockHotelProviderAdapter(str(fixture_path)).fetch_hotels()
