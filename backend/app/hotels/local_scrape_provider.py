from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from app.hotels.contracts import (
    HotelProviderAdapter,
    ProviderCapabilities,
    ProviderHotelRecord,
    ProviderRateRecord,
)
from app.hotels._local_scrape_html import extract_json_ld_documents
from app.hotels._local_scrape_jsonld import hotel_records_from_document


class LocalHtmlHotelProviderAdapter(HotelProviderAdapter):
    provider_id = "local_scrape"

    def __init__(
        self,
        *,
        fixture_path: str,
        check_in: date,
        check_out: date,
        guests: int = 2,
    ) -> None:
        if check_out <= check_in:
            raise ValueError("hotel_local_scrape_stay_invalid")
        if guests < 1:
            raise ValueError("hotel_local_scrape_guests_invalid")
        self._fixture_path = Path(fixture_path)
        self._check_in = check_in
        self._check_out = check_out
        self._guests = guests

    @classmethod
    def from_environment(cls) -> LocalHtmlHotelProviderAdapter:
        fixture_path = os.getenv("HOTEL_LOCAL_SCRAPE_PATH", "").strip()
        check_in = _read_date_env("HOTEL_LOCAL_SCRAPE_CHECK_IN")
        check_out = _read_date_env("HOTEL_LOCAL_SCRAPE_CHECK_OUT")
        guests = _read_positive_int_env("HOTEL_LOCAL_SCRAPE_GUESTS", default=2)
        return cls(
            fixture_path=fixture_path or str(Path(__file__).resolve().parent / "fixtures" / "local_scrape_hotels.html"),
            check_in=check_in,
            check_out=check_out,
            guests=guests,
        )

    def is_enabled(self) -> bool:
        return self._fixture_path.is_file() and self._fixture_path.suffix.lower() in {".htm", ".html"}

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            contract_version=self.contract_version,
            supports_catalog=True,
            supports_area_search=False,
            supports_hotel_rates=True,
            supports_direct_revalidation=True,
            supports_parameterized_occupancy=False,
            supports_multiple_rooms=False,
            supports_children_ages=False,
            supports_total_fees=False,
            supports_room_type=True,
            supports_meal_plan=False,
            supports_cancellation_policy=True,
            supports_availability_status=True,
            supports_partner_deeplink=True,
        )

    def fetch_hotels(self) -> list[ProviderHotelRecord]:
        if not self.is_enabled():
            return []
        documents = extract_json_ld_documents(self._fixture_path.read_text(encoding="utf-8-sig", errors="replace"))
        return [
            record
            for document in documents
            for record in hotel_records_from_document(
                document=document,
                check_in=self._check_in,
                check_out=self._check_out,
                guests=self._guests,
            )
        ]

    def fetch_hotel_rates(
        self,
        hotel_id: str,
        check_in: date,
        check_out: date,
        guests: int = 2,
        currency: str = "EUR",
    ) -> list[ProviderRateRecord]:
        if (check_in, check_out, guests) != (self._check_in, self._check_out, self._guests):
            return []
        for hotel in self.fetch_hotels():
            if hotel.provider_hotel_id == hotel_id:
                return [rate for rate in hotel.rates if rate.currency == currency.strip().upper()]
        return []


def _read_date_env(name: str) -> date:
    raw_value = os.getenv(name, "").strip()
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError(f"hotel_local_scrape_{name.lower()}_invalid") from exc


def _read_positive_int_env(name: str, *, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"hotel_local_scrape_{name.lower()}_invalid") from exc
    if value < 1:
        raise ValueError(f"hotel_local_scrape_{name.lower()}_invalid")
    return value
