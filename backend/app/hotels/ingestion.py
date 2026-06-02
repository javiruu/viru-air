from __future__ import annotations

import json
import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hotels.contracts import HotelProviderAdapter
from app.hotels.makcorps_provider import MakcorpsHotelProviderAdapter
from app.hotels.mapping import HotelMappingService
from app.hotels.mock_provider import MockHotelProviderAdapter
from app.infrastructure.db.models import HotelProviderAlias, HotelRateSnapshot


def resolve_hotel_provider() -> HotelProviderAdapter:
    feature_enabled = os.getenv("HOTEL_FEATURE_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    if not feature_enabled:
        raise ValueError("HOTEL_FEATURE_ENABLED is false. Hotels module is disabled.")

    provider = os.getenv("HOTEL_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        fixture_path = os.getenv("HOTEL_MOCK_FIXTURE_PATH")
        adapter = MockHotelProviderAdapter(fixture_path=fixture_path)
        if adapter.is_enabled():
            return adapter
        raise ValueError("HOTEL_PROVIDER=mock is not enabled.")
    if provider == "makcorps":
        adapter = MakcorpsHotelProviderAdapter()
        if adapter.is_enabled():
            return adapter
        raise ValueError(
            "HOTEL_PROVIDER=makcorps is not enabled. Set MAKCORPS_API_KEY to activate."
        )
    raise ValueError(f"Unsupported hotel provider '{provider}'. Expected: mock, makcorps")


@dataclass
class IngestedHotelSummary:
    provider_hotel_id: str
    hotel_id: str
    confidence_score: float
    is_ambiguous: bool
    rates_ingested: int


@dataclass
class HotelIngestionResult:
    provider_id: str
    hotels_processed: int
    rates_ingested: int
    ambiguous_matches: int
    items: list[IngestedHotelSummary]


class HotelIngestionService:
    def __init__(self, db: Session, provider: HotelProviderAdapter | None = None) -> None:
        self._db = db
        self._provider = provider if provider is not None else resolve_hotel_provider()

    def ingest(self) -> HotelIngestionResult:
        records = self._provider.fetch_hotels()
        mapping_service = HotelMappingService(self._db)

        items: list[IngestedHotelSummary] = []
        total_rates = 0
        ambiguous = 0

        for record in records:
            alias = self._db.scalar(
                select(HotelProviderAlias).where(
                    HotelProviderAlias.provider == self._provider.provider_id,
                    HotelProviderAlias.provider_hotel_id == record.provider_hotel_id,
                )
            )
            if alias is not None:
                hotel_id = alias.hotel_id
                confidence_score = float(alias.confidence_score or 1.0)
                is_ambiguous = False
            else:
                mapped = mapping_service.map_or_create(record)
                hotel_id = mapped.hotel.id
                confidence_score = mapped.confidence_score
                is_ambiguous = mapped.is_ambiguous
                if is_ambiguous:
                    ambiguous += 1

                alias = HotelProviderAlias(
                    hotel_id=hotel_id,
                    provider=self._provider.provider_id,
                    provider_hotel_id=record.provider_hotel_id,
                    raw_name=record.raw_name,
                    raw_address=record.raw_address,
                    raw_payload=json.dumps(record.raw_payload or {}, ensure_ascii=False, separators=(",", ":")),
                    confidence_score=confidence_score,
                )
                self._db.add(alias)
                self._db.flush()

            rates_for_hotel = 0
            for rate in record.rates:
                snapshot = self._db.scalar(
                    select(HotelRateSnapshot).where(
                        HotelRateSnapshot.hotel_id == hotel_id,
                        HotelRateSnapshot.provider == self._provider.provider_id,
                        HotelRateSnapshot.check_in == rate.check_in,
                        HotelRateSnapshot.check_out == rate.check_out,
                        HotelRateSnapshot.guests == rate.guests,
                        HotelRateSnapshot.currency == rate.currency,
                        HotelRateSnapshot.amount == rate.amount,
                    )
                )
                if snapshot is not None:
                    continue

                self._db.add(
                    HotelRateSnapshot(
                        hotel_id=hotel_id,
                        provider=self._provider.provider_id,
                        check_in=rate.check_in,
                        check_out=rate.check_out,
                        guests=rate.guests,
                        room_label=rate.room_label,
                        meal_plan=rate.meal_plan,
                        cancellation_policy=rate.cancellation_policy,
                        currency=rate.currency,
                        amount=rate.amount,
                    )
                )
                rates_for_hotel += 1
                total_rates += 1

            items.append(
                IngestedHotelSummary(
                    provider_hotel_id=record.provider_hotel_id,
                    hotel_id=hotel_id,
                    confidence_score=confidence_score,
                    is_ambiguous=is_ambiguous,
                    rates_ingested=rates_for_hotel,
                )
            )

        self._db.commit()
        return HotelIngestionResult(
            provider_id=self._provider.provider_id,
            hotels_processed=len(records),
            rates_ingested=total_rates,
            ambiguous_matches=ambiguous,
            items=items,
        )
