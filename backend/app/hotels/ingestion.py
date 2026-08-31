from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hotels.activation import is_hotel_provider_external, resolve_hotel_activation
from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord, ProviderRateRecord
from app.hotels.fault_profiles import HotelFaultProfileError
from app.hotels.makcorps_provider import MakcorpsHotelProviderAdapter
from app.hotels.local_scrape_provider import LocalHtmlHotelProviderAdapter
from app.hotels.overpass_provider import OverpassHotelProviderAdapter
from app.hotels.mapping import HotelMappingService
from app.hotels.mock_provider import MockHotelProviderAdapter
from app.hotels.stay_offer import CancellationPolicy, OfferIdentity, RoomSignature, stay_query_from_legacy
from app.infrastructure.db.models import HotelProviderAlias, HotelRateSnapshot, HotelStayOffer, utc_now_naive
from app.services.hotel_provider_budget import HotelProviderBudgetLedger, policy_from_env
from app.services.hotel_provider_latency import ProviderLatencySample, measure_provider_call


class HotelIngestionBudgetDeniedError(ValueError):
    """Raised before an external provider ingestion call is made."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"hotel_provider_budget_denied:{provider}:ingestion")


def resolve_hotel_provider(*, provider: str | None = None) -> HotelProviderAdapter:
    activation = resolve_hotel_activation(operation="ingestion", provider=provider)
    if not activation.feature_enabled or not activation.external_calls_allowed:
        messages = {
            "provider_not_explicitly_enabled": f"HOTEL_PROVIDER={activation.provider} is not explicitly enabled.",
            "invalid_profile": f"HOTEL_PROFILE={activation.profile} is invalid. Hotel operations are disabled.",
            "invalid_profile_configuration": f"HOTEL_PROVIDER={activation.provider} is not allowed for HOTEL_PROFILE={activation.profile}.",
            "invalid_provider": f"Unsupported hotel provider '{activation.provider}'. Expected: mock, local_scrape, makcorps, osm_overpass",
            "profile_prod_off": "HOTEL_PROFILE=prod_off. Hotel provider ingestion and sweeps are disabled.",
            "hotel_feature_disabled": "HOTEL_FEATURE_ENABLED is false. Hotel provider ingestion and sweeps are disabled.",
        }
        raise ValueError(messages.get(activation.reason, "Hotel provider ingestion is disabled."))

    provider = activation.provider
    adapter: HotelProviderAdapter
    if provider == "mock":
        fixture_path = os.getenv("HOTEL_MOCK_FIXTURE_PATH")
        adapter = MockHotelProviderAdapter(
            fixture_path=fixture_path,
            fault_profile=os.getenv("HOTEL_MOCK_FAULT_PROFILE"),
            fault_profile_path=os.getenv("HOTEL_MOCK_FAULT_PROFILE_PATH"),
        )
        if adapter.is_enabled():
            return adapter
        raise ValueError("HOTEL_PROVIDER=mock is not enabled.")
    if provider == "local_scrape":
        adapter = LocalHtmlHotelProviderAdapter.from_environment()
        if adapter.is_enabled():
            return adapter
        raise ValueError("HOTEL_PROVIDER=local_scrape requires a readable local HTML file.")
    if provider == "makcorps":
        adapter = MakcorpsHotelProviderAdapter()
        if adapter.is_enabled():
            return adapter
        raise ValueError(
            "HOTEL_PROVIDER=makcorps is not enabled. Set MAKCORPS_API_KEY to activate."
        )
    if provider == "osm_overpass":
        adapter = OverpassHotelProviderAdapter.from_environment()
        if adapter.is_enabled():
            return adapter
        raise ValueError("HOTEL_PROVIDER=osm_overpass is not enabled.")
    raise ValueError(f"Unsupported hotel provider '{provider}'. Expected: mock, local_scrape, makcorps, osm_overpass")


@dataclass
class IngestedHotelSummary:
    provider_hotel_id: str
    hotel_id: str
    confidence_score: float
    is_ambiguous: bool
    rates_ingested: int
    warnings: list[str] = field(default_factory=list)
    needs_review: bool = False


@dataclass
class HotelIngestionResult:
    provider_id: str
    hotels_processed: int
    rates_ingested: int
    ambiguous_matches: int
    items: list[IngestedHotelSummary]
    warnings: list[dict[str, object]] = field(default_factory=list)
    needs_review: bool = False
    fault_profile: str | None = None
    provider_run_id: str | None = None


class HotelIngestionService:
    def __init__(
        self,
        db: Session,
        provider: HotelProviderAdapter | None = None,
        provider_run_id: str | None = None,
        outcome_sink: dict[str, object] | None = None,
        latency_sink: Callable[[ProviderLatencySample], None] | None = None,
    ) -> None:
        self._db = db
        self._provider = provider if provider is not None else resolve_hotel_provider()
        activation = resolve_hotel_activation(
            operation="ingestion", provider=self._provider.provider_id
        )
        if not activation.feature_enabled or not activation.external_calls_allowed:
            if activation.reason == "hotel_feature_disabled":
                raise ValueError(
                    "HOTEL_FEATURE_ENABLED is false. Hotel provider ingestion and sweeps are disabled."
                )
            raise ValueError(
                f"HOTEL_PROVIDER={self._provider.provider_id} is not enabled for ingestion."
            )
        if not self._provider.is_enabled():
            raise ValueError(
                f"HOTEL_PROVIDER={self._provider.provider_id} adapter is not enabled."
            )
        self._provider_run_id = provider_run_id
        self._outcome_sink = outcome_sink
        self._latency_sink = latency_sink

    def _classify_provider_result(self, value: list[ProviderHotelRecord]) -> tuple[str, str | None]:
        if not value:
            return "empty", None
        profile = getattr(self._provider, "fault_profile", "happy_path")
        if profile in {"partial_batch", "hotel_ambiguous"}:
            return "partial", profile
        return "success", None

    @staticmethod
    def _classify_provider_exception(exc: Exception) -> tuple[str, str]:
        if isinstance(exc, HotelFaultProfileError):
            return exc.profile.expected_status, exc.error_code
        error_code = getattr(exc, "error_code", None)
        if error_code == "rate_limited":
            return "rate_limited", error_code
        if error_code == "timeout":
            return "timeout", error_code
        if error_code == "invalid_response":
            return "invalid_response", error_code
        if error_code == "provider_unavailable":
            return "unavailable", error_code
        return "failed", "provider_fetch_failed"

    def _get_or_create_canonical_stay_offer(
        self,
        *,
        hotel_id: str,
        provider_hotel_id: str,
        rate: ProviderRateRecord,
    ) -> HotelStayOffer | None:
        if not (
            rate.provider_offer_id
            and rate.price_semantics == "total"
            and rate.amount_total is not None
            and rate.conditions_completeness == "complete"
        ):
            return None

        stay_query = stay_query_from_legacy(
            canonical_hotel_id=hotel_id,
            area_key=None,
            check_in=rate.check_in,
            check_out=rate.check_out,
            guests=rate.guests,
            currency=rate.currency,
        )
        offer_identity = OfferIdentity(
            provider_id=self._provider.provider_id,
            provider_hotel_id=provider_hotel_id,
            provider_offer_id=rate.provider_offer_id,
            stay_query=stay_query,
            room=RoomSignature(
                room_type_normalized=rate.room_type_normalized,
                room_label_raw=rate.room_label,
            ),
            meal_plan_normalized=rate.meal_plan_normalized,
            cancellation=CancellationPolicy(
                cancellation_type=rate.cancellation_type,
                conditions_completeness=rate.conditions_completeness,
                policy_text_raw=rate.cancellation_policy,
            ),
        )
        stay_offer = self._db.scalar(
            select(HotelStayOffer).where(
                HotelStayOffer.provider == self._provider.provider_id,
                HotelStayOffer.provider_hotel_id == provider_hotel_id,
                HotelStayOffer.stay_query_fingerprint == stay_query.fingerprint,
                HotelStayOffer.offer_fingerprint == offer_identity.fingerprint,
            )
        )
        if stay_offer is not None:
            return stay_offer

        canonical_query = {
            "check_in": stay_query.check_in.isoformat(),
            "check_out": stay_query.check_out.isoformat(),
            "occupancy": {
                "source": stay_query.occupancy.source,
                **stay_query.occupancy.fingerprint_payload(),
            },
            "currency": stay_query.currency,
            "provider_offer_id": rate.provider_offer_id,
            "room_label": rate.room_label,
            "meal_plan": rate.meal_plan,
            "cancellation_policy": rate.cancellation_policy,
        }
        stay_offer = HotelStayOffer(
            canonical_hotel_id=hotel_id,
            provider=self._provider.provider_id,
            provider_hotel_id=provider_hotel_id,
            stay_query_fingerprint=stay_query.fingerprint,
            offer_fingerprint=offer_identity.fingerprint,
            canonical_query_json=json.dumps(canonical_query, sort_keys=True, separators=(",", ":")),
            conditions_completeness=rate.conditions_completeness,
            fee_semantics=rate.price_semantics,
        )
        self._db.add(stay_offer)
        self._db.flush()
        return stay_offer

    def _increment_outcome(self, key: str) -> None:
        if self._outcome_sink is None:
            return
        current = self._outcome_sink.get(key, 0)
        self._outcome_sink[key] = current + 1 if isinstance(current, int) else 1

    def ingest(self) -> HotelIngestionResult:
        reservation = None
        if is_hotel_provider_external(self._provider.provider_id):
            budget = HotelProviderBudgetLedger(self._db)
            reservation = budget.reserve(policy_from_env(self._provider.provider_id, "ingestion"))
            if not reservation.allowed:
                self._increment_outcome("provider_fetch_budget_denied")
                raise HotelIngestionBudgetDeniedError(self._provider.provider_id)
            # The adapter call is about to happen, so the admission becomes
            # consumed before any provider I/O. It can no longer be counted
            # against the outstanding reservation.
            if not budget.consume(reservation):
                raise RuntimeError("hotel_provider_budget_consume_failed")
            self._increment_outcome("provider_fetch_attempted")
        measurement = measure_provider_call(
            self._provider.fetch_hotels,
            provider=self._provider.provider_id,
            operation="ingestion",
            classify_result=self._classify_provider_result,
            classify_exception=self._classify_provider_exception,
            on_sample=self._latency_sink,
            propagate_exception=True,
        )
        assert measurement is not None
        records = measurement.value or []
        if self._outcome_sink is not None and is_hotel_provider_external(self._provider.provider_id):
            self._increment_outcome("provider_fetch_completed")
            if not records:
                self._increment_outcome("provider_fetch_empty")
        mapping_service = HotelMappingService(self._db)

        items: list[IngestedHotelSummary] = []
        warnings: list[dict[str, object]] = []
        total_rates = 0
        ambiguous = 0
        profile_name = getattr(self._provider, "fault_profile", "happy_path")
        batch_warning = profile_name == "partial_batch"
        profile_requires_review = profile_name in {"hotel_ambiguous", "partial_batch"}

        for record in records:
            alias = self._db.scalar(
                select(HotelProviderAlias).where(
                    HotelProviderAlias.provider == self._provider.provider_id,
                    HotelProviderAlias.provider_hotel_id == record.provider_hotel_id,
                )
            )
            alias_confidence = float(alias.confidence_score) if alias and alias.confidence_score is not None else 1.0
            pending_alias = alias if alias is not None and alias_confidence == 0 else None
            if alias is not None and pending_alias is None:
                hotel_id = alias.hotel_id
                confidence_score = alias_confidence
                is_ambiguous = False
            else:
                mapped = mapping_service.map_or_create(record)
                hotel_id = mapped.hotel.id
                confidence_score = mapped.confidence_score
                is_ambiguous = mapped.is_ambiguous or profile_name == "hotel_ambiguous"

                # A pending marker is retried on each ingestion. When mapping
                # becomes confident, promote the same row instead of creating
                # a duplicate alias; when it remains ambiguous, retain its
                # original hotel identity and zero-confidence safety gate.
                if pending_alias is not None and mapped.is_ambiguous:
                    if mapped.hotel.id != pending_alias.hotel_id:
                        self._db.delete(mapped.hotel)
                        self._db.flush()
                    hotel_id = pending_alias.hotel_id
                    confidence_score = 0.0
                if is_ambiguous:
                    ambiguous += 1

                alias = pending_alias or HotelProviderAlias(
                    hotel_id=hotel_id,
                    provider=self._provider.provider_id,
                    provider_hotel_id=record.provider_hotel_id,
                )
                alias.hotel_id = hotel_id
                alias.raw_name = record.raw_name
                alias.raw_address = record.raw_address
                alias.raw_payload = json.dumps(
                    {
                        **(record.raw_payload or {}),
                        "mapping_status": "needs_review" if is_ambiguous else "confirmed",
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                alias.confidence_score = 0.0 if is_ambiguous else confidence_score
                if pending_alias is None:
                    self._db.add(alias)
                self._db.flush()

            rates_for_hotel = 0
            for rate in record.rates:
                stay_offer = self._get_or_create_canonical_stay_offer(
                    hotel_id=hotel_id,
                    provider_hotel_id=record.provider_hotel_id,
                    rate=rate,
                )
                snapshot_filters = [
                    HotelRateSnapshot.hotel_id == hotel_id,
                    HotelRateSnapshot.provider == self._provider.provider_id,
                    HotelRateSnapshot.check_in == rate.check_in,
                    HotelRateSnapshot.check_out == rate.check_out,
                    HotelRateSnapshot.guests == rate.guests,
                    HotelRateSnapshot.currency == rate.currency,
                    HotelRateSnapshot.amount == rate.amount,
                ]
                if stay_offer is not None:
                    snapshot_filters.append(HotelRateSnapshot.offer_fingerprint == stay_offer.offer_fingerprint)
                if self._provider_run_id is not None:
                    snapshot_filters.append(
                        HotelRateSnapshot.provider_run_id == self._provider_run_id
                    )
                snapshot = self._db.scalar(
                    select(HotelRateSnapshot).where(*snapshot_filters)
                )
                if snapshot is not None:
                    continue

                self._db.add(
                    HotelRateSnapshot(
                        hotel_id=hotel_id,
                        stay_offer_id=stay_offer.id if stay_offer is not None else None,
                        provider_run_id=self._provider_run_id,
                        provider=self._provider.provider_id,
                        check_in=rate.check_in,
                        check_out=rate.check_out,
                        guests=rate.guests,
                        room_label=rate.room_label,
                        meal_plan=rate.meal_plan,
                        cancellation_policy=rate.cancellation_policy,
                        currency=rate.currency,
                        amount=rate.amount,
                        amount_total=rate.amount_total if stay_offer is not None else None,
                        availability_status=rate.availability_status,
                        observed_at=utc_now_naive() if stay_offer is not None else None,
                        stay_query_fingerprint=stay_offer.stay_query_fingerprint if stay_offer is not None else None,
                        offer_fingerprint=stay_offer.offer_fingerprint if stay_offer is not None else None,
                        snapshot_outcome="success" if stay_offer is not None else None,
                        price_semantics=rate.price_semantics if stay_offer is not None else None,
                        conditions_completeness=rate.conditions_completeness if stay_offer is not None else None,
                        deep_link=rate.deep_link,
                    )
                )
                rates_for_hotel += 1
                total_rates += 1

            item_warnings: list[str] = []
            if is_ambiguous:
                item_warnings.append("hotel_ambiguous")
            if profile_name == "hotel_ambiguous" and "hotel_ambiguous" not in item_warnings:
                item_warnings.append("hotel_ambiguous")
            if profile_name == "stale_history":
                item_warnings.append("stale_history")
            if batch_warning:
                item_warnings.append("partial_batch")

            item_needs_review = is_ambiguous or profile_requires_review
            if item_warnings:
                warnings.append(
                    {
                        "provider_hotel_id": record.provider_hotel_id,
                        "hotel_id": hotel_id,
                        "codes": item_warnings,
                    }
                )

            items.append(
                IngestedHotelSummary(
                    provider_hotel_id=record.provider_hotel_id,
                    hotel_id=hotel_id,
                    confidence_score=confidence_score,
                    is_ambiguous=is_ambiguous,
                    rates_ingested=rates_for_hotel,
                    warnings=item_warnings,
                    needs_review=item_needs_review,
                )
            )

        self._db.commit()
        return HotelIngestionResult(
            provider_id=self._provider.provider_id,
            hotels_processed=len(records),
            rates_ingested=total_rates,
            ambiguous_matches=ambiguous,
            items=items,
            warnings=warnings,
            needs_review=profile_requires_review or any(item.needs_review for item in items),
            fault_profile=profile_name,
        )
