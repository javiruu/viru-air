from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord, ProviderRateRecord
from app.hotels.fault_profiles import (
    HotelFaultProfileError,
    exception_for_profile,
    resolve_hotel_fault_profile,
)


class MockHotelProviderAdapter(HotelProviderAdapter):
    provider_id = "mock"

    def __init__(
        self,
        fixture_path: str | None = None,
        *,
        fault_profile: str | None = None,
        fault_profile_path: str | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        self._fixture_path = Path(fixture_path) if fixture_path else base_dir / "fixtures" / "mock_hotels.json"
        self._fault_profile = resolve_hotel_fault_profile(fault_profile, path=fault_profile_path)

    def is_enabled(self) -> bool:
        return True

    @property
    def fault_profile(self) -> str:
        return self._fault_profile.name

    def fetch_hotels(self) -> list[ProviderHotelRecord]:
        profile = self._fault_profile
        if profile.mode == "empty":
            return []
        if profile.mode == "raise":
            raise exception_for_profile(profile)

        try:
            payload = json.loads(self._fixture_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise HotelFaultProfileError(profile, "hotel_mock_invalid_json") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("hotels"), list):
            raise HotelFaultProfileError(profile, "hotel_mock_schema_drift")
        if profile.mode == "partial":
            payload = dict(payload)
            payload["hotels"] = payload["hotels"][: max(1, len(payload["hotels"]) // 2)]
        records: list[ProviderHotelRecord] = []
        for item in payload.get("hotels", []):
            provider_hotel_id = str(item["provider_hotel_id"]).strip()
            raw_name = str(item["name"]).strip()
            city = str(item["city"]).strip()
            country_code = str(item["country_code"]).strip().upper()

            if not provider_hotel_id:
                raise ValueError("Mock hotel fixture contains an empty provider_hotel_id.")
            if not raw_name:
                raise ValueError(f"Mock hotel fixture contains an empty name for provider_hotel_id={provider_hotel_id}")
            if not city:
                raise ValueError(f"Mock hotel fixture contains an empty city for provider_hotel_id={provider_hotel_id}")
            if len(country_code) != 2 or not country_code.isalpha():
                raise ValueError(
                    f"Invalid country_code '{country_code}' for provider_hotel_id={provider_hotel_id}"
                )

            rates: list[ProviderRateRecord] = []
            for rate in item.get("rates", []):
                if not isinstance(rate, dict):
                    raise HotelFaultProfileError(profile, "hotel_mock_schema_drift")
                if profile.name == "rate_without_currency" and "currency" in rate:
                    rate = {key: value for key, value in rate.items() if key != "currency"}
                if profile.name == "sold_out":
                    rate = {**rate, "availability_status": "unavailable"}
                if profile.name == "deeplink_invalid":
                    rate = {**rate, "deep_link": "javascript:alert(1)"}
                if profile.name == "stale_history":
                    rate = {**rate, "availability_status": "stale"}
                check_in = date.fromisoformat(rate["check_in"])
                check_out = date.fromisoformat(rate["check_out"])
                if profile.name == "rate_without_currency" and "currency" not in rate:
                    raise exception_for_profile(profile)
                currency = str(rate.get("currency", "EUR")).strip().upper()
                if len(currency) != 3 or not currency.isalpha():
                    raise ValueError(
                        f"Invalid currency '{currency}' for provider_hotel_id={provider_hotel_id}"
                    )
                if check_out <= check_in:
                    raise ValueError(
                        f"Invalid stay range for provider_hotel_id={provider_hotel_id}: "
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
                        availability_status=str(rate.get("availability_status", "available")),
                        deep_link=rate.get("deep_link"),
                        provider_offer_id=rate.get("provider_offer_id"),
                        room_type_normalized=str(rate.get("room_type_normalized", "unknown")),
                        meal_plan_normalized=str(rate.get("meal_plan_normalized", "UNKNOWN")),
                        cancellation_type=str(rate.get("cancellation_type", "unknown")),
                        price_semantics=str(rate.get("price_semantics", "unknown")),
                        amount_total=(float(rate["amount_total"]) if rate.get("amount_total") is not None else None),
                        conditions_completeness=str(rate.get("conditions_completeness", "unknown")),
                    )
                )
            records.append(
                ProviderHotelRecord(
                    provider_hotel_id=provider_hotel_id,
                    raw_name=raw_name,
                    raw_address=(str(item["address"]).strip() if item.get("address") is not None else None) or None,
                    city=city,
                    country_code=country_code,
                    latitude=float(item["latitude"]) if item.get("latitude") is not None else None,
                    longitude=float(item["longitude"]) if item.get("longitude") is not None else None,
                    stars=int(item["stars"]) if item.get("stars") is not None else None,
                    rates=rates,
                    raw_payload=item,
                )
            )
        return records

    def fetch_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int = 2,
        currency: str = "EUR",
    ) -> list[ProviderRateRecord]:
        """Return fixture rates matching one targeted stay.

        Reusing ``fetch_hotels`` keeps the declarative fault profile behavior
        identical for ingestion and revalidation while ensuring the fixture is
        never mutated. An unmatched hotel or stay is a valid empty response.
        """
        requested_currency = currency.strip().upper()
        for hotel in self.fetch_hotels():
            if hotel.provider_hotel_id != hotel_id:
                continue
            return [
                rate
                for rate in hotel.rates
                if rate.check_in == check_in
                and rate.check_out == check_out
                and rate.guests == guests
                and rate.currency == requested_currency
            ]
        return []

