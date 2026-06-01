from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord, ProviderRateRecord


class MockHotelProviderAdapter(HotelProviderAdapter):
    provider_id = "mock"

    def __init__(self, fixture_path: str | None = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self._fixture_path = Path(fixture_path) if fixture_path else base_dir / "fixtures" / "mock_hotels.json"

    def is_enabled(self) -> bool:
        return True

    def fetch_hotels(self) -> list[ProviderHotelRecord]:
        payload = json.loads(self._fixture_path.read_text(encoding="utf-8-sig"))
        records: list[ProviderHotelRecord] = []
        for item in payload.get("hotels", []):
            rates: list[ProviderRateRecord] = []
            for rate in item.get("rates", []):
                check_in = date.fromisoformat(rate["check_in"])
                check_out = date.fromisoformat(rate["check_out"])
                currency = str(rate.get("currency", "EUR")).strip().upper()
                if len(currency) != 3 or not currency.isalpha():
                    raise ValueError(
                        f"Invalid currency '{currency}' for provider_hotel_id={item.get('provider_hotel_id')}"
                    )
                if check_out <= check_in:
                    raise ValueError(
                        f"Invalid stay range for provider_hotel_id={item.get('provider_hotel_id')}: "
                        f"check_out ({check_out}) must be after check_in ({check_in})"
                    )
                rates.append(
                    ProviderRateRecord(
                        check_in=check_in,
                        check_out=check_out,
                        amount=float(rate["amount"]),
                        currency=currency,
                        guests=int(rate.get("guests", 2)),
                        room_label=rate.get("room_label"),
                        meal_plan=rate.get("meal_plan"),
                        cancellation_policy=rate.get("cancellation_policy"),
                    )
                )
            records.append(
                ProviderHotelRecord(
                    provider_hotel_id=str(item["provider_hotel_id"]),
                    raw_name=str(item["name"]),
                    raw_address=item.get("address"),
                    city=str(item["city"]),
                    country_code=str(item["country_code"]).upper(),
                    latitude=float(item["latitude"]) if item.get("latitude") is not None else None,
                    longitude=float(item["longitude"]) if item.get("longitude") is not None else None,
                    stars=int(item["stars"]) if item.get("stars") is not None else None,
                    rates=rates,
                    raw_payload=item,
                )
            )
        return records

