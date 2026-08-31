from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import os
import re
from datetime import date as Date, datetime, time, timedelta
from contextvars import copy_context
from dataclasses import dataclass
from threading import Lock
from typing import Callable, TypedDict, cast
from uuid import uuid4

from app.core.request_context import (
    get_client_event_id,
    get_correlation_id,
    normalize_client_event_id,
    normalize_correlation_id,
)

from sqlalchemy import Select, and_, asc, case, delete, desc, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.hotels.activation import (
    is_hotel_provider_external,
    is_hotel_canonical_dual_write_enabled,
    is_hotel_sweep_enabled,
    resolve_hotel_activation,
)
from app.hotels.canonical_tracking import write_canonical_tracking_watch
from app.i18n import t
from app.hotels.contracts import HotelProviderAdapter, ProviderRateRecord
from app.hotels.fault_profiles import HotelFaultProfileError
from app.hotels.geo import HotelGeoService, HotelNearbySuggestion, haversine_km
from app.hotels.normalization import HotelNormalizationService
from app.hotels.ingestion import HotelIngestionBudgetDeniedError, HotelIngestionService
from app.hotels.mock_provider import MockHotelProviderAdapter
from app.hotels.parity import HotelParityService, ParitySignal
from app.hotels.partner_links import sanitize_hotel_deep_link
from app.services.hotel_observability_metrics import (
    METRIC_ALERT_EVENT,
    METRIC_SWEEP_RUN,
    record_hotel_daily_metric,
)
from app.services.hotel_provider_budget import HotelProviderBudgetLedger, policy_from_env
from app.services.hotel_provider_latency import (
    HotelProviderLatencyAccumulator,
    ProviderLatencySample,
    compose_provider_latency_sinks,
    measure_provider_call,
    persist_hotel_provider_latency_aggregates,
)
from app.services.hotel_provider_circuit import HotelCircuitPermit, HotelProviderCircuitStore
from app.services.hotel_sweep_lease import (
    HotelSweepLeaseStore,
    HotelSweepLeaseToken,
    stay_query_fingerprint,
)
from app.infrastructure.db.models import (
    HotelAlertEvent,
    HotelAlertRule,
    HotelNotificationDelivery,
    HotelCompSet,
    HotelCompSetMember,
    HotelProperty,
    HotelProviderAlias,
    HotelProviderRun,
    HotelRateSnapshot,
    HotelSavedSearch,
    HotelStayOffer,
    HotelTrackedOffer,
    HotelTrackedOfferLifecycleEvent,
    HotelUserStayWatch,
    HotelWatchlistItem,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HotelAlertTrace:
    """Private observability projection for a user-owned hotel alert event."""

    event_id: str
    provider_run_id: str | None
    correlation_id: str | None
    client_event_id: str | None


@dataclass(frozen=True, slots=True)
class HotelTrackedOfferStatus:
    offer: HotelTrackedOffer
    latest_snapshot: HotelRateSnapshot | None
    state: str
    warning_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HotelObservationFreshness:
    state: str
    observed_at: datetime | None
    age_seconds: int | None
    expires_at: datetime | None
    provenance_kind: str
    requires_revalidation: bool


@dataclass(frozen=True, slots=True)
class HotelObservationFreshnessInput:
    observed_at: datetime | None
    collected_at: datetime | None
    provider: str | None
    now: datetime | None = None


@dataclass(frozen=True, slots=True)
class HotelTrackedOfferCreation:
    offer: HotelTrackedOffer
    created: bool


class HotelAreaResolveResult(TypedDict):
    area_label: str
    latitude: float
    longitude: float
    country_code: str
    confidence: str
    source: str


class HotelAreaPriceInfo(TypedDict):
    provider: str | None
    amount: float | None
    currency: str
    price_semantics: str | None
    amount_total: float | None
    observed_at: datetime | None
    snapshot_outcome: str | None
    conditions_completeness: str | None


class HotelAreaSearchResult(TypedDict):
    hotel_id: str
    canonical_name: str
    city: str
    country_code: str
    stars: int | None
    distance_km: float
    lowest_price: float | None
    displayed_price: float | None
    currency: str
    provider: str | None
    price_semantics: str | None
    amount_total: float | None
    observed_at: datetime | None
    snapshot_outcome: str | None
    conditions_completeness: str | None
    check_in: Date
    check_out: Date
    guests: int
    has_tracking: bool


def classify_hotel_observation_freshness(
    observation: HotelObservationFreshnessInput,
) -> HotelObservationFreshness:
    effective_observed_at = observation.observed_at or observation.collected_at
    if effective_observed_at is None:
        return HotelObservationFreshness("unknown", None, None, None, "unknown", True)
    if (observation.provider or "").lower().startswith("mock"):
        return HotelObservationFreshness(
            "historical",
            effective_observed_at,
            None,
            None,
            "fixture_demo",
            True,
        )
    current_time = observation.now or utc_now_naive()
    age_seconds = int((current_time - effective_observed_at).total_seconds())
    if age_seconds < 0:
        return HotelObservationFreshness("unknown", effective_observed_at, None, None, "unknown", True)
    freshness_expires_at = effective_observed_at + timedelta(hours=6)
    if age_seconds <= 30 * 60:
        state = "fresh"
    elif age_seconds <= 6 * 60 * 60:
        state = "recent"
    elif age_seconds <= 24 * 60 * 60:
        state = "stale"
    else:
        state = "expired"
    return HotelObservationFreshness(
        state,
        effective_observed_at,
        age_seconds,
        freshness_expires_at,
        "provider_observed" if observation.observed_at is not None else "historical_snapshot",
        state in {"stale", "expired"},
    )


@dataclass(frozen=True, slots=True)
class HotelTrackedOfferLifecycleTransition:
    offer: HotelTrackedOffer
    outcome: str


_HOTEL_SECRET_PATTERN = re.compile(
    r"(?i)([\"']?(?:api[_-]?key|token|secret|authorization)[\"']?\s*[:=]\s*[\"']?)([^&\s,}\"']+)"
)


def _sanitize_hotel_error(error: object) -> str:
    return _HOTEL_SECRET_PATTERN.sub(r"\1***", str(error)[:500])


def _classify_hotel_revalidation_exception(exc: Exception) -> tuple[str, str]:
    """Map provider/profile errors to the bounded latency taxonomy."""
    error_code = getattr(exc, "error_code", "provider_fetch_failed")
    if error_code == "timeout":
        return "timeout", "timeout"
    if error_code == "rate_limited":
        return "rate_limited", "rate_limited"
    if error_code in {"invalid_response", "schema_drift", "rate_without_currency"}:
        return "invalid_response", error_code
    return "failed", error_code


def _record_hotel_circuit_outcome(
    db: Session,
    permit: HotelCircuitPermit,
    outcome: str,
) -> bool:
    recorded = HotelProviderCircuitStore(db).record(
        permit,
        outcome,
        now=utc_now_naive(),
    )
    if not recorded:
        logger.warning(
            "hotel_provider_circuit_outcome_not_recorded provider=%s operation=%s outcome=%s",
            permit.provider,
            permit.operation,
            outcome,
        )
    return recorded


def search_hotels(
    db: Session,
    *,
    q: str | None,
    city: str | None,
    country_code: str | None,
    limit: int,
    offset: int,
) -> list[HotelProperty]:
    stmt = select(HotelProperty)
    if q:
        normalized = HotelNormalizationService.normalize_text(q)
        stmt = stmt.where(HotelProperty.normalized_name.contains(normalized))
    if city:
        normalized_city = HotelNormalizationService.normalize_city(city)
        if normalized_city:
            stmt = stmt.where(HotelProperty.normalized_city.contains(normalized_city))
    if country_code:
        stmt = stmt.where(HotelProperty.country_code == country_code)
    stmt = stmt.order_by(HotelProperty.canonical_name.asc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def get_hotel_or_404(db: Session, hotel_id: str) -> HotelProperty:
    hotel = db.get(HotelProperty, hotel_id)
    if not hotel:
        raise ValueError("hotel_not_found")
    return hotel


def list_hotel_rates(
    db: Session,
    *,
    hotel_id: str,
    check_in: object | None,
    check_out: object | None,
) -> list[HotelRateSnapshot]:
    stmt = select(HotelRateSnapshot).where(
        HotelRateSnapshot.hotel_id == hotel_id,
        HotelRateSnapshot.tracked_offer_id.is_(None),
    )
    if check_in is not None:
        stmt = stmt.where(HotelRateSnapshot.check_in >= check_in)
    if check_out is not None:
        stmt = stmt.where(HotelRateSnapshot.check_out <= check_out)
    stmt = stmt.order_by(desc(HotelRateSnapshot.collected_at), desc(HotelRateSnapshot.id))
    return list(db.scalars(stmt))


def ingest_hotels_mock(db: Session, *, provider_run_id: str | None = None):
    """Run explicit mock ingestion and link its observations to a provider run.

    Direct ``HotelIngestionService`` callers remain fixture-friendly and do not
    create runs. The API operation uses this wrapper so its request intent is
    persisted without changing read-only catalog searches.
    """
    provider = MockHotelProviderAdapter(
        fixture_path=os.getenv("HOTEL_MOCK_FIXTURE_PATH"),
        fault_profile=os.getenv("HOTEL_MOCK_FAULT_PROFILE"),
        fault_profile_path=os.getenv("HOTEL_MOCK_FAULT_PROFILE_PATH"),
    )
    if provider_run_id is not None:
        return HotelIngestionService(
            db,
            provider=provider,
            provider_run_id=provider_run_id,
        ).ingest()

    provider_run = HotelProviderRun(
        provider="mock",
        correlation_id=normalize_correlation_id(get_correlation_id()) if get_correlation_id() else None,
        client_event_id=normalize_client_event_id(get_client_event_id()),
        execution_id=str(uuid4()),
        status="running",
        tracked_outcomes={
            "provider_fetch_attempted": 0,
            "provider_fetch_completed": 0,
            "provider_fetch_empty": 0,
            "provider_fetch_failed": 0,
            "provider_fetch_skipped": 0,
            "provider_fetch_budget_denied": 0,
        },
    )
    db.add(provider_run)
    db.flush()
    latency_accumulator = HotelProviderLatencyAccumulator()
    try:
        result = HotelIngestionService(
            db,
            provider=provider,
            provider_run_id=provider_run.id,
            latency_sink=latency_accumulator.add,
        ).ingest()
        provider_run.items_processed = result.hotels_processed
        provider_run.status = "completed"
        provider_run.finished_at = utc_now_naive()
        provider_run.tracked_outcomes = dict(provider_run.tracked_outcomes or {})
        provider_run.tracked_outcomes["snapshots_created"] = result.rates_ingested
        provider_run.tracked_outcomes["ambiguous_matches"] = result.ambiguous_matches
        provider_run.tracked_outcomes["warnings"] = result.warnings
        provider_run.tracked_outcomes["warning_count"] = len(result.warnings)
        provider_run.tracked_outcomes["needs_review"] = result.needs_review
        provider_run.tracked_outcomes["fault_profile"] = result.fault_profile
        if result.fault_profile in {"hotel_ambiguous", "partial_batch"}:
            provider_run.status = "partial"
        try:
            with db.begin_nested():
                persist_hotel_provider_latency_aggregates(
                    db,
                    provider_run_id=provider_run.id,
                    accumulator=latency_accumulator,
                )
        except Exception:
            logger.warning("hotel_provider_latency_persistence_failed")
        db.add(provider_run)
        db.commit()
        db.refresh(provider_run)
        result.provider_run_id = provider_run.id
        return result
    except Exception as exc:
        # Ingestion may have flushed aliases/snapshots before a provider or
        # validation error. Discard that partial transaction before recording
        # the terminal run state, so a failed run never publishes half a batch.
        db.rollback()
        provider_run.status = "failed"
        provider_run.error_message = _sanitize_hotel_error(exc)
        provider_run.finished_at = utc_now_naive()
        # Failed runs retain only the safe aggregates collected before the
        # terminal error; persistence remains in the same final transaction.
        db.add(provider_run)
        db.flush()
        try:
            with db.begin_nested():
                persist_hotel_provider_latency_aggregates(
                    db,
                    provider_run_id=provider_run.id,
                    accumulator=latency_accumulator,
                )
        except Exception:
            logger.warning("hotel_provider_latency_persistence_failed")
        db.commit()
        raise


def list_watchlist(db: Session, user_id: str) -> list[HotelWatchlistItem]:
    return list(
        db.scalars(
            select(HotelWatchlistItem)
            .where(HotelWatchlistItem.user_id == user_id)
            .order_by(desc(HotelWatchlistItem.created_at), desc(HotelWatchlistItem.id))
        )
    )


def add_watchlist_item(db: Session, *, user_id: str, hotel_id: str, label: str | None) -> HotelWatchlistItem:
    _ = get_hotel_or_404(db, hotel_id)
    item = HotelWatchlistItem(user_id=user_id, hotel_id=hotel_id, label=label)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("hotel_watchlist_item_already_exists") from exc
    db.refresh(item)
    return item


def delete_watchlist_item(db: Session, *, user_id: str, item_id: str) -> None:
    item = db.scalar(select(HotelWatchlistItem).where(HotelWatchlistItem.id == item_id))
    if not item:
        raise ValueError("hotel_watchlist_item_not_found")
    if item.user_id != user_id:
        raise PermissionError("not_allowed")
    db.delete(item)
    db.commit()


_SAVED_SEARCH_SCHEMA_VERSION = "hotel-search-v1"
_SAVED_SEARCH_STATUSES = frozenset({"active", "paused"})
_SAVED_SEARCH_PARAMS = frozenset({
    "mode", "q", "city", "area", "area_lat", "area_lng", "area_country",
    "area_confidence", "area_source", "check_in", "check_out", "guests", "radius", "provider",
})


def _canonical_saved_search_query(query: dict[str, object]) -> tuple[str, str]:
    if set(query) != {"schema", "params"} or query.get("schema") != _SAVED_SEARCH_SCHEMA_VERSION:
        raise ValueError("invalid_saved_search_query")
    raw_params = query.get("params")
    if not isinstance(raw_params, dict) or not raw_params or set(raw_params) - _SAVED_SEARCH_PARAMS:
        raise ValueError("invalid_saved_search_query")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in raw_params.items()):
        raise ValueError("invalid_saved_search_query")
    if len(json.dumps(query, ensure_ascii=False, separators=(",", ":"))) > 8_000:
        raise ValueError("invalid_saved_search_query")

    params = {key: value.strip() for key, value in raw_params.items() if value.strip()}
    max_lengths = {
        "q": 120,
        "city": 100,
        "area": 120,
        "area_country": 2,
        "area_confidence": 40,
        "area_source": 40,
        "check_in": 10,
        "check_out": 10,
        "guests": 2,
        "radius": 2,
        "provider": 5,
    }
    if any(len(value) > max_lengths.get(key, 120) for key, value in params.items()):
        raise ValueError("invalid_saved_search_query")
    if "area_country" in params:
        area_country = params["area_country"].upper()
        if len(area_country) != 2 or not area_country.isalpha():
            raise ValueError("invalid_saved_search_query")
        params["area_country"] = area_country
    mode = params.get("mode", "name").lower()
    if mode not in {"name", "area"}:
        raise ValueError("invalid_saved_search_query")
    params["mode"] = mode
    if mode == "area":
        if not params.get("area"):
            raise ValueError("invalid_saved_search_query")
        if not params.get("check_in") or not params.get("check_out"):
            raise ValueError("invalid_saved_search_query")
        params.pop("q", None)
        params.pop("city", None)
        for field in ("area_lat", "area_lng"):
            try:
                numeric = float(params[field])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid_saved_search_query") from exc
            if field == "area_lat" and not -90 <= numeric <= 90:
                raise ValueError("invalid_saved_search_query")
            if field == "area_lng" and not -180 <= numeric <= 180:
                raise ValueError("invalid_saved_search_query")
            params[field] = format(numeric, ".6f").rstrip("0").rstrip(".")
    elif not (params.get("q") or params.get("city")):
        raise ValueError("invalid_saved_search_query")
    else:
        for field in ("area", "area_lat", "area_lng", "area_country", "area_confidence", "area_source"):
            params.pop(field, None)

    for field in ("check_in", "check_out"):
        if field in params:
            try:
                Date.fromisoformat(params[field])
            except ValueError as exc:
                raise ValueError("invalid_saved_search_query") from exc
    if ("check_in" in params) != ("check_out" in params):
        raise ValueError("invalid_saved_search_query")
    if "check_in" in params and params["check_out"] <= params["check_in"]:
        raise ValueError("invalid_saved_search_query")

    try:
        guests = int(params.get("guests", "2"))
        radius = int(params.get("radius", "10"))
    except ValueError as exc:
        raise ValueError("invalid_saved_search_query") from exc
    if not 1 <= guests <= 20 or not 1 <= radius <= 50:
        raise ValueError("invalid_saved_search_query")
    if guests != 2:
        params["guests"] = str(guests)
    else:
        params.pop("guests", None)
    if radius != 10:
        params["radius"] = str(radius)
    else:
        params.pop("radius", None)

    if params.get("provider") not in {None, "1", "true"}:
        raise ValueError("invalid_saved_search_query")
    if params.get("provider") == "true":
        params["provider"] = "1"
    canonical_query = {"schema": _SAVED_SEARCH_SCHEMA_VERSION, "params": params}
    payload = json.dumps(canonical_query, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def list_saved_hotel_searches(db: Session, *, user_id: str) -> list[HotelSavedSearch]:
    return list(
        db.scalars(
            select(HotelSavedSearch)
            .where(HotelSavedSearch.user_id == user_id)
            .order_by(desc(HotelSavedSearch.updated_at), desc(HotelSavedSearch.id))
        )
    )


def get_saved_hotel_search_or_404(db: Session, *, user_id: str, saved_search_id: str) -> HotelSavedSearch:
    row = db.scalar(select(HotelSavedSearch).where(HotelSavedSearch.id == saved_search_id))
    if row is None:
        raise ValueError("hotel_saved_search_not_found")
    if row.user_id != user_id:
        raise PermissionError("not_allowed")
    return row


def create_saved_hotel_search(
    db: Session,
    *,
    user_id: str,
    schema_version: str,
    query: dict[str, object],
    label: str | None,
) -> HotelSavedSearch:
    if schema_version != _SAVED_SEARCH_SCHEMA_VERSION:
        raise ValueError("unsupported_saved_search_version")
    if label is not None and (not isinstance(label, str) or len(label) > 120):
        raise ValueError("invalid_saved_search_label")
    canonical_query_json, fingerprint = _canonical_saved_search_query(query)
    existing = db.scalar(
        select(HotelSavedSearch).where(
            HotelSavedSearch.user_id == user_id,
            HotelSavedSearch.fingerprint == fingerprint,
        )
    )
    if existing is not None:
        existing.last_used_at = utc_now_naive()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = HotelSavedSearch(
        user_id=user_id,
        schema_version=schema_version,
        fingerprint=fingerprint,
        canonical_query_json=canonical_query_json,
        label=label.strip() if label and label.strip() else None,
        status="active",
        last_used_at=utc_now_naive(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(HotelSavedSearch).where(
                HotelSavedSearch.user_id == user_id,
                HotelSavedSearch.fingerprint == fingerprint,
            )
        )
        if existing is None:
            raise ValueError("saved_search_create_conflict") from exc
        return existing
    db.refresh(row)
    return row


def update_saved_hotel_search(
    db: Session,
    *,
    user_id: str,
    saved_search_id: str,
    update_data: dict[str, object],
) -> HotelSavedSearch:
    row = get_saved_hotel_search_or_404(db, user_id=user_id, saved_search_id=saved_search_id)
    if "label" in update_data:
        label = update_data["label"]
        row.label = label.strip() if isinstance(label, str) and label.strip() else None
    if "status" in update_data:
        status = update_data["status"]
        if status not in _SAVED_SEARCH_STATUSES:
            raise ValueError("invalid_saved_search_status")
        row.status = str(status)
    row.updated_at = utc_now_naive()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_saved_hotel_search(db: Session, *, user_id: str, saved_search_id: str) -> None:
    row = get_saved_hotel_search_or_404(db, user_id=user_id, saved_search_id=saved_search_id)
    db.delete(row)
    db.commit()


def list_comp_sets(db: Session, user_id: str) -> list[HotelCompSet]:
    return list(
        db.scalars(
            select(HotelCompSet).where(HotelCompSet.user_id == user_id).order_by(desc(HotelCompSet.created_at), desc(HotelCompSet.id))
        )
    )


def create_comp_set(db: Session, *, user_id: str, name: str, anchor_hotel_id: str) -> HotelCompSet:
    _ = get_hotel_or_404(db, anchor_hotel_id)
    comp_set = HotelCompSet(user_id=user_id, name=name.strip(), anchor_hotel_id=anchor_hotel_id)
    db.add(comp_set)
    db.commit()
    db.refresh(comp_set)
    return comp_set


def get_comp_set_or_404(db: Session, *, user_id: str, comp_set_id: str) -> HotelCompSet:
    comp_set = db.scalar(select(HotelCompSet).where(HotelCompSet.id == comp_set_id))
    if not comp_set:
        raise ValueError("hotel_comp_set_not_found")
    if comp_set.user_id != user_id:
        raise PermissionError("not_allowed")
    return comp_set


def get_nearby_comp_set_suggestions(
    db: Session,
    *,
    user_id: str,
    comp_set_id: str,
    radius_km: int = 5,
    limit: int = 6,
) -> list[HotelNearbySuggestion]:
    service = HotelGeoService(db)
    return service.suggest_for_comp_set(
        user_id=user_id,
        comp_set_id=comp_set_id,
        radius_km=radius_km,
        limit=limit,
    )


def list_comp_set_members(db: Session, comp_set_id: str) -> list[HotelCompSetMember]:
    return list(db.scalars(select(HotelCompSetMember).where(HotelCompSetMember.comp_set_id == comp_set_id).order_by(HotelCompSetMember.id.asc())))


def add_comp_set_member(db: Session, *, user_id: str, comp_set_id: str, hotel_id: str) -> HotelCompSetMember:
    comp_set = get_comp_set_or_404(db, user_id=user_id, comp_set_id=comp_set_id)
    _ = get_hotel_or_404(db, hotel_id)
    if hotel_id == comp_set.anchor_hotel_id:
        raise ValueError("hotel_comp_set_anchor_cannot_be_member")
    member = HotelCompSetMember(comp_set_id=comp_set_id, hotel_id=hotel_id)
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("hotel_comp_set_member_already_exists") from exc
    db.refresh(member)
    return member


def delete_comp_set_member(db: Session, *, user_id: str, comp_set_id: str, member_id: str) -> None:
    _ = get_comp_set_or_404(db, user_id=user_id, comp_set_id=comp_set_id)
    member = db.scalar(select(HotelCompSetMember).where(HotelCompSetMember.id == member_id, HotelCompSetMember.comp_set_id == comp_set_id))
    if not member:
        raise ValueError("hotel_comp_set_member_not_found")
    db.delete(member)
    db.commit()


def delete_comp_set(db: Session, *, user_id: str, comp_set_id: str) -> None:
    comp_set = get_comp_set_or_404(db, user_id=user_id, comp_set_id=comp_set_id)
    db.delete(comp_set)
    db.commit()


def list_alert_rules(db: Session, user_id: str) -> list[HotelAlertRule]:
    return list(db.scalars(select(HotelAlertRule).where(HotelAlertRule.user_id == user_id).order_by(HotelAlertRule.id.asc())))


def create_alert_rule(
    db: Session,
    *,
    user_id: str,
    hotel_id: str,
    rule_type: str,
    threshold_amount: float | None,
    threshold_percent: float | None,
    is_active: bool,
    tracked_offer_id: str | None = None,
    compare_against: str = "snapshot_previous",
    cooldown_minutes: int = 60,
) -> HotelAlertRule:
    _ = get_hotel_or_404(db, hotel_id)
    if tracked_offer_id is not None:
        tracked_offer = get_tracked_offer_or_404(
            db,
            user_id=user_id,
            tracked_offer_id=tracked_offer_id,
        )
        if tracked_offer.hotel_id != hotel_id:
            raise ValueError("hotel_alert_rule_tracked_offer_hotel_mismatch")
    rule = HotelAlertRule(
        user_id=user_id,
        hotel_id=hotel_id,
        tracked_offer_id=tracked_offer_id,
        rule_type=rule_type,
        threshold_amount=threshold_amount,
        threshold_percent=threshold_percent,
        compare_against=compare_against,
        cooldown_minutes=cooldown_minutes,
        is_active=is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_alert_rule(
    db: Session,
    *,
    user_id: str,
    rule_id: str,
    update_data: dict[str, object],
) -> HotelAlertRule:
    rule = db.scalar(select(HotelAlertRule).where(HotelAlertRule.id == rule_id))
    if not rule:
        raise ValueError("hotel_alert_rule_not_found")
    if rule.user_id != user_id:
        raise PermissionError("not_allowed")

    for field, value in update_data.items():
        if field not in {"rule_type", "threshold_amount", "threshold_percent", "compare_against", "cooldown_minutes", "is_active"}:
            continue
        setattr(rule, field, value)

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def delete_alert_rule(db: Session, *, user_id: str, rule_id: str) -> None:
    rule = db.scalar(select(HotelAlertRule).where(HotelAlertRule.id == rule_id))
    if not rule:
        raise ValueError("hotel_alert_rule_not_found")
    if rule.user_id != user_id:
        raise PermissionError("not_allowed")
    db.delete(rule)
    db.commit()


def get_hotel_parity(db: Session, *, hotel_id: str) -> list[ParitySignal]:
    _ = get_hotel_or_404(db, hotel_id)
    rates = list_hotel_rates(db, hotel_id=hotel_id, check_in=None, check_out=None)
    return HotelParityService.compute_parity(rates)


def get_hotel_provider_run_or_404(db: Session, provider_run_id: str) -> HotelProviderRun:
    provider_run = db.get(HotelProviderRun, provider_run_id)
    if provider_run is None:
        raise ValueError("hotel_provider_run_not_found")
    return provider_run


def run_hotel_sweep(
    db: Session,
    *,
    provider: str = "mock",
    correlation_id: str | None = None,
    execution_id: str | None = None,
    latency_sink: Callable[[ProviderLatencySample], None] | None = None,
) -> HotelProviderRun:
    inherited_correlation_id = get_correlation_id()
    effective_correlation_id = (
        normalize_correlation_id(correlation_id or inherited_correlation_id)
        if correlation_id or inherited_correlation_id
        else None
    )
    effective_execution_id = normalize_correlation_id(execution_id) if execution_id else str(uuid4())
    provider_run = HotelProviderRun(
        provider=provider,
        correlation_id=effective_correlation_id,
        # A sweep evaluates rules across users. It must never carry a browser
        # intent because provider-run ownership is intentionally global.
        client_event_id=None,
        execution_id=effective_execution_id,
        status="running",
        tracked_outcomes={
            "offers_scanned": 0,
            "snapshots_created": 0,
            "provider_fetch_attempted": 0,
            "provider_fetch_completed": 0,
            "provider_fetch_empty": 0,
            "provider_fetch_failed": 0,
            "provider_fetch_skipped": 0,
            "provider_fetch_budget_denied": 0,
        },
    )
    if provider not in {"mock", "local_scrape", "makcorps", "osm_overpass"}:
        provider_run.status = "failed"
        provider_run.error_message = _sanitize_hotel_error(f"Unsupported sweep provider: {provider}")
        provider_run.finished_at = utc_now_naive()
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_SWEEP_RUN,
            provider="unknown",
            outcome=provider_run.status,
        )
        db.add(provider_run)
        db.commit()
        db.refresh(provider_run)
        return provider_run

    activation = resolve_hotel_activation(operation="sweep", provider=provider)
    if not is_hotel_sweep_enabled(provider=provider):
        provider_run.status = "failed"
        if activation.reason == "hotel_feature_disabled":
            provider_run.error_message = "HOTEL_FEATURE_ENABLED is false. Hotel sweeps are disabled."
        elif activation.reason == "provider_not_explicitly_enabled":
            provider_run.error_message = "The selected hotel provider is not explicitly enabled. Hotel sweeps are disabled."
        elif activation.reason == "provider_operation_unsupported":
            provider_run.error_message = "The selected hotel provider supports catalog ingestion only. Hotel sweeps are disabled."
        else:
            provider_run.error_message = "HOTEL_SWEEP_ENABLED is false. Hotel sweeps are disabled."
        provider_run.finished_at = utc_now_naive()
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_SWEEP_RUN,
            provider=provider_run.provider,
            outcome=provider_run.status,
        )
        db.add(provider_run)
        db.commit()
        db.refresh(provider_run)
        return provider_run
    db.add(provider_run)
    db.flush()
    latency_accumulator = HotelProviderLatencyAccumulator()
    effective_latency_sink = compose_provider_latency_sinks(
        latency_sink,
        latency_accumulator.add,
    )
    # Keep the aggregate in a plain local dictionary while provider/DB calls
    # flush the session. SQLAlchemy may expire a JSON attribute during those
    # operations; the local sink is the authoritative run accumulator.
    run_outcomes = dict(provider_run.tracked_outcomes or {})

    adapter = None
    sweep_outcomes: dict[str, int] = {}
    try:
        from app.hotels.ingestion import resolve_hotel_provider

        adapter = resolve_hotel_provider(provider=provider)
        result = HotelIngestionService(
            db,
            provider=adapter,
            provider_run_id=provider_run.id,
            outcome_sink=run_outcomes,
            latency_sink=effective_latency_sink,
        ).ingest()

        provider_run.items_processed = result.hotels_processed
        provider_run.status = "completed"
        result_ambiguous_matches = getattr(result, "ambiguous_matches", 0)
        result_warnings = getattr(result, "warnings", [])
        result_needs_review = getattr(result, "needs_review", False)
        run_outcomes["ambiguous_matches"] = result_ambiguous_matches
        run_outcomes["warnings"] = result_warnings
        run_outcomes["warning_count"] = len(result_warnings)
        run_outcomes["needs_review"] = result_needs_review
        run_outcomes["fault_profile"] = getattr(result, "fault_profile", None)
        provider_run.tracked_outcomes = dict(run_outcomes)
        db.flush()

        evaluate_hotel_alerts(db, provider_run_id=provider_run.id)
        # Persist the per-offer provider outcome for workers and the admin
        # operational endpoint.
        sweep_outcomes = sweep_tracked_offers(
            db,
            provider_run_id=provider_run.id,
            provider_adapter=adapter,
            outcome_sink=run_outcomes,
            latency_sink=effective_latency_sink,
        )
        # Merge immediately after the sweep, before any later query can expire
        # or refresh the mutable JSON attribute. Assigning a fresh dict makes
        # the aggregate visible to SQLAlchemy and to the persisted run.
        merged_outcomes = dict(run_outcomes)
        for key, value in sweep_outcomes.items():
            merged_outcomes[key] = max(merged_outcomes.get(key, 0), value)
        run_outcomes = merged_outcomes
        provider_run.tracked_outcomes = dict(run_outcomes)
        provider_run.tracked_outcomes["warning_count"] = len(
            provider_run.tracked_outcomes.get("warnings", [])
        ) if isinstance(provider_run.tracked_outcomes.get("warnings"), list) else 0
        provider_run.tracked_outcomes["needs_review"] = bool(
            provider_run.tracked_outcomes.get("needs_review", False)
        )
        db.add(provider_run)
        materialize_hotel_delivery_intents(db, provider_run_id=provider_run.id)
        # Keep the aggregate run state honest: a completed ingestion is not
        # a fully completed tracking pass when targeted units degraded.
        outcomes = run_outcomes
        # A valid empty response is a completed unit outcome. Only provider
        # failures and mapping/adapter skips degrade the aggregate run.
        has_failed = outcomes.get("provider_fetch_failed", 0) > 0
        has_skipped = (
            outcomes.get("provider_fetch_skipped", 0) > 0
            or outcomes.get("provider_fetch_budget_denied", 0) > 0
        )
        has_partial_item_review = outcomes.get("fault_profile") in {
            "hotel_ambiguous",
            "partial_batch",
        }
        if has_failed or has_skipped or has_partial_item_review:
            if outcomes.get("snapshots_created", 0) > 0 or has_partial_item_review:
                provider_run.status = "partial"
            elif has_failed:
                provider_run.status = "failed"
            else:
                provider_run.status = "skipped"
    except HotelIngestionBudgetDeniedError as exc:
        provider_run.status = "skipped"
        provider_run.error_message = _sanitize_hotel_error(exc)
        provider_run.tracked_outcomes = dict(run_outcomes)
        provider_run.finished_at = utc_now_naive()
        db.flush()

    except Exception as exc:
        provider_run.status = "failed"
        provider_run.error_message = _sanitize_hotel_error(exc)
        outcomes = dict(run_outcomes)
        for key, value in sweep_outcomes.items():
            outcomes[key] = max(outcomes.get(key, 0), value)
        outcomes["provider_fetch_failed"] = max(1, outcomes.get("provider_fetch_failed", 0))
        provider_run.tracked_outcomes = outcomes
        db.flush()

    provider_run.finished_at = utc_now_naive()
    try:
        with db.begin_nested():
            persist_hotel_provider_latency_aggregates(
                db,
                provider_run_id=provider_run.id,
                accumulator=latency_accumulator,
            )
    except Exception:
        # Observability must not turn a completed provider run into a failed run.
        logger.warning("hotel_provider_latency_persistence_failed")

    record_hotel_daily_metric(
        db,
        metric_name=METRIC_SWEEP_RUN,
        provider=provider_run.provider,
        outcome=provider_run.status,
    )
    db.commit()
    db.refresh(provider_run)
    return provider_run


def sweep_tracked_offers(
    db: Session,
    *,
    provider_run_id: str,
    provider_adapter: HotelProviderAdapter | None = None,
    outcome_sink: dict[str, object] | None = None,
    latency_sink: Callable[[ProviderLatencySample], None] | None = None,
) -> dict[str, int]:
    """Sweep active tracked offers: create snapshots from matching rates and update current_price.

    For each active HotelTrackedOffer with check_in/check_out set, this function:
    1. If a provider_adapter with fetch_hotel_rates is available, tries to fetch
       targeted rates for the specific hotel/dates/guests/currency.
    2. Otherwise, finds the cheapest matching HotelRateSnapshot from the general pool
       (same hotel, dates, guests, currency, not yet linked to any tracked offer).
    3. Creates a new snapshot linked to the tracked_offer_id and provider_run_id.
    4. Updates current_price on the tracked offer.
    5. Creates an alert event if the price changed from the previous snapshot.

    Returns a dict with counts for scanned offers, snapshots, and provider
    fetch outcomes. A provider fetch is counted as completed even when it
    returns no rates; empty/error responses never fall back to local history.
    """
    active_offers = list(
        db.scalars(
            select(HotelTrackedOffer).where(
                HotelTrackedOffer.is_active.is_(True),
                HotelTrackedOffer.lifecycle_state == _TRACKING_LIFECYCLE_ACTIVE,
                HotelTrackedOffer.check_in.is_not(None),
                HotelTrackedOffer.check_out.is_not(None),
            )
        )
    )

    offers_scanned = 0
    snapshots_created = 0
    provider_fetch_attempted = 0
    provider_fetch_completed = 0
    provider_fetch_empty = 0
    provider_fetch_failed = 0
    provider_fetch_skipped = 0
    provider_fetch_budget_denied = 0
    profile_error_counts: dict[str, int] = {}
    budget_ledger = HotelProviderBudgetLedger(db)

    def _add_item_warning(hotel_id: str, provider_hotel_id: str | None, code: str) -> None:
        if outcome_sink is None:
            return
        warnings = outcome_sink.setdefault("warnings", [])
        if not isinstance(warnings, list) or len(warnings) >= 100:
            return
        for warning in warnings:
            if (
                isinstance(warning, dict)
                and warning.get("hotel_id") == hotel_id
                and code in warning.get("codes", [])
            ):
                return
        warnings.append(
            {
                "provider_hotel_id": provider_hotel_id,
                "hotel_id": hotel_id,
                "codes": [code],
            }
        )
        outcome_sink["warning_count"] = len(warnings)
        if code in {"hotel_ambiguous", "partial_batch"}:
            outcome_sink["needs_review"] = True
    def _outcome_count(key: str) -> int:
        value = (outcome_sink or {}).get(key, 0)
        return value if isinstance(value, int) else 0

    outcome_baseline = {
        key: _outcome_count(key)
        for key in (
            "offers_scanned",
            "snapshots_created",
            "provider_fetch_attempted",
            "provider_fetch_completed",
            "provider_fetch_empty",
            "provider_fetch_failed",
            "provider_fetch_skipped",
            "provider_fetch_budget_denied",
        )
    }

    def _sync_outcomes() -> None:
        if outcome_sink is not None:
            outcome_sink.update(
                {
                    "offers_scanned": outcome_baseline["offers_scanned"] + offers_scanned,
                    "snapshots_created": outcome_baseline["snapshots_created"] + snapshots_created,
                    "provider_fetch_attempted": outcome_baseline["provider_fetch_attempted"] + provider_fetch_attempted,
                    "provider_fetch_completed": outcome_baseline["provider_fetch_completed"] + provider_fetch_completed,
                    "provider_fetch_empty": outcome_baseline["provider_fetch_empty"] + provider_fetch_empty,
                    "provider_fetch_failed": outcome_baseline["provider_fetch_failed"] + provider_fetch_failed,
                    "provider_fetch_skipped": outcome_baseline["provider_fetch_skipped"] + provider_fetch_skipped,
                    "provider_fetch_budget_denied": outcome_baseline["provider_fetch_budget_denied"] + provider_fetch_budget_denied,
                    **profile_error_counts,
                }
            )

    for offer in active_offers:
        offers_scanned += 1
        _sync_outcomes()

        stay_check_in = offer.check_in
        stay_check_out = offer.check_out
        if stay_check_in is None or stay_check_out is None:
            continue

        # Fetch targeted rates only after resolving the provider's external
        # hotel identity. Never send our internal HotelProperty.id to a
        # provider: an absent/ambiguous alias is a mapping skip, not a
        # provider query. Non-mock offers also require a matching adapter;
        # they must never fall back to a different provider's local history.
        provider_rates: list[ProviderRateRecord] = []
        external_provider_blocked = is_hotel_provider_external(offer.provider)
        provider_id = provider_adapter.provider_id if provider_adapter is not None else None
        provider_alias = None
        query_lease = None
        adapter_profile = str(getattr(provider_adapter, "fault_profile", ""))

        if provider_adapter is not None:
            adapter = provider_adapter
            if provider_id == offer.provider:
                provider_aliases = list(
                    db.scalars(
                        select(HotelProviderAlias).where(
                            HotelProviderAlias.hotel_id == offer.hotel_id,
                            HotelProviderAlias.provider == provider_id,
                        )
                    )
                )
                # Zero or multiple aliases are mapping outcomes, never a
                # reason to guess an external ID or call the provider.
                if (
                    len(provider_aliases) == 1
                    and provider_aliases[0].provider_hotel_id
                    and (
                        provider_aliases[0].confidence_score is None
                        or float(provider_aliases[0].confidence_score) > 0
                    )
                ):
                    provider_alias = provider_aliases[0]
                else:
                    provider_fetch_skipped += 1
                    _sync_outcomes()
            else:
                provider_fetch_skipped += 1
                _sync_outcomes()

            if adapter_profile in {"hotel_ambiguous", "partial_batch"}:
                _add_item_warning(
                    offer.hotel_id,
                    provider_alias.provider_hotel_id if provider_alias is not None else None,
                    adapter_profile,
                )

            if provider_alias is not None:
                reservation = None
                circuit_permit: HotelCircuitPermit | None = None
                if is_hotel_provider_external(offer.provider):
                    circuit = HotelProviderCircuitStore(db)
                    admission = circuit.admit(
                        offer.provider,
                        "revalidation",
                        now=utc_now_naive(),
                    )
                    if not admission.allowed or admission.permit is None:
                        provider_fetch_skipped += 1
                        _sync_outcomes()
                        continue
                    circuit_permit = admission.permit
                    reservation = budget_ledger.reserve(
                        policy_from_env(offer.provider, "revalidation")
                    )
                    if not reservation.allowed:
                        provider_fetch_budget_denied += 1
                        _sync_outcomes()
                        continue
                    query_fingerprint = stay_query_fingerprint(
                        provider=offer.provider,
                        operation="revalidation",
                        canonical_hotel_id=offer.hotel_id,
                        provider_hotel_id=provider_alias.provider_hotel_id,
                        check_in=stay_check_in,
                        check_out=stay_check_out,
                        guests=offer.guests or 2,
                        currency=offer.currency or "EUR",
                        room_label=offer.room_label,
                        meal_plan=offer.meal_plan,
                        cancellation_policy=offer.cancellation_policy,
                    )
                    query_lease = HotelSweepLeaseStore(db).acquire(
                        query_fingerprint,
                        now=utc_now_naive(),
                        ttl_seconds=60,
                    )
                    if query_lease is None:
                        provider_fetch_skipped += 1
                        budget_ledger.release(reservation)
                        _sync_outcomes()
                        continue
                    if not budget_ledger.consume(reservation):
                        # The adapter was never called; return the admission so
                        # a transient ledger failure cannot strand capacity.
                        budget_ledger.release(reservation)
                        provider_fetch_failed += 1
                        HotelSweepLeaseStore(db).finish(
                            query_lease,
                            status="failed",
                            now=utc_now_naive(),
                            provider_run_id=provider_run_id,
                            error_code="budget_consume_failed",
                        )
                        _sync_outcomes()
                        continue
                provider_fetch_attempted += 1
                _sync_outcomes()
                try:
                    measurement = measure_provider_call(
                        lambda: adapter.fetch_hotel_rates(
                            hotel_id=provider_alias.provider_hotel_id,
                            check_in=stay_check_in,
                            check_out=stay_check_out,
                            guests=offer.guests or 2,
                            currency=offer.currency or "EUR",
                        ),
                        provider=offer.provider,
                        operation="revalidation",
                        classify_result=lambda value: ("empty" if not value else "success", None),
                        classify_exception=_classify_hotel_revalidation_exception,
                        on_sample=latency_sink,
                        propagate_exception=True,
                    )
                    assert measurement is not None
                    provider_rates = measurement.value or []
                    provider_fetch_completed += 1
                    if any(rate.availability_status == "stale" for rate in provider_rates):
                        _add_item_warning(
                            offer.hotel_id,
                            provider_alias.provider_hotel_id if provider_alias is not None else None,
                            "stale_history",
                        )
                    if circuit_permit is not None:
                        _record_hotel_circuit_outcome(
                            db,
                            circuit_permit,
                            "success" if provider_rates else "empty",
                        )
                    _sync_outcomes()
                    if query_lease is not None:
                        lease_store = HotelSweepLeaseStore(db)
                        if not lease_store.owns_active_lease(query_lease, now=utc_now_naive()):
                            provider_fetch_skipped += 1
                            _sync_outcomes()
                            continue
                    # An empty provider response is a completed negative
                    # observation, not permission to reuse historical data.
                    if not provider_rates:
                        provider_fetch_empty += 1
                        # A provider-confirmed empty response, including the
                        # Mock empty fault profile, is not permission to reuse
                        # an older local snapshot.
                        external_provider_blocked = True
                        _sync_outcomes()
                        if query_lease is not None:
                            HotelSweepLeaseStore(db).finish(
                                query_lease,
                                status="done",
                                now=utc_now_naive(),
                                provider_run_id=provider_run_id,
                            )
                        if is_hotel_provider_external(offer.provider):
                            external_provider_blocked = True
                    else:
                        external_provider_blocked = False
                except Exception as exc:
                    provider_fetch_failed += 1
                    error_code = getattr(exc, "error_code", "provider_fetch_failed")
                    if isinstance(exc, HotelFaultProfileError):
                        profile_key = f"provider_fetch_error_{error_code}"
                        profile_error_counts[profile_key] = profile_error_counts.get(profile_key, 0) + 1
                    if circuit_permit is not None:
                        _record_hotel_circuit_outcome(db, circuit_permit, "failed")
                    _sync_outcomes()
                    if query_lease is not None:
                        HotelSweepLeaseStore(db).finish(
                            query_lease,
                            status="failed",
                            now=utc_now_naive(),
                            provider_run_id=provider_run_id,
                            error_code=error_code,
                        )
                    # A typed Mock fault is an intentional provider outcome,
                    # not a reason to reuse local history. Preserve the legacy
                    # fallback only for generic errors raised by custom local
                    # test adapters.
                    if is_hotel_provider_external(offer.provider) or isinstance(exc, HotelFaultProfileError):
                        external_provider_blocked = True
        elif is_hotel_provider_external(offer.provider):
            provider_fetch_skipped += 1
            _sync_outcomes()

        # Determine the rate to use: provider rates first, then fallback to unlinked snapshots
        eligible_provider_rates = [
            rate
            for rate in provider_rates
            if rate.availability_status not in {"unavailable", "stale"}
        ]
        if provider_rates:
            # Prefer an eligible rate for price updates. If every provider
            # observation is sold out/stale, retain the cheapest observation so
            # availability history is recorded without making it an eligible
            # current price.
            best = min(eligible_provider_rates or provider_rates, key=lambda r: r.amount)
            rate_amount = best.amount
            rate_provider = provider_adapter.provider_id if provider_adapter is not None else "makcorps"
            rate_room = best.room_label or offer.room_label
            rate_meal = best.meal_plan or offer.meal_plan
            rate_cancellation = best.cancellation_policy or offer.cancellation_policy
            rate_check_in = best.check_in
            rate_check_out = best.check_out
            rate_currency = best.currency
            rate_guests = best.guests
            rate_availability = best.availability_status
            rate_deep_link = sanitize_hotel_deep_link(
                best.deep_link,
                provider=rate_provider,
            )
        elif not external_provider_blocked:
            # Local/mock fallback: find the cheapest matching unlinked
            # snapshot. External provider failures and mapping skips never
            # masquerade as a fresh observation.
            cheapest = db.scalars(
                select(HotelRateSnapshot)
                .where(
                    HotelRateSnapshot.hotel_id == offer.hotel_id,
                    HotelRateSnapshot.provider == offer.provider,
                    HotelRateSnapshot.check_in == offer.check_in,
                    HotelRateSnapshot.check_out == offer.check_out,
                    HotelRateSnapshot.guests == offer.guests,
                    HotelRateSnapshot.currency == offer.currency,
                    HotelRateSnapshot.availability_status.notin_(["unavailable", "stale"]),
                    HotelRateSnapshot.tracked_offer_id.is_(None),
                )
                .order_by(HotelRateSnapshot.amount.asc())
                .limit(1)
            ).first()

            if cheapest is None:
                continue

            rate_amount = float(cheapest.amount)
            rate_provider = cheapest.provider
            rate_room = cheapest.room_label or offer.room_label
            rate_meal = cheapest.meal_plan or offer.meal_plan
            rate_cancellation = cheapest.cancellation_policy or offer.cancellation_policy
            rate_check_in = cheapest.check_in
            rate_check_out = cheapest.check_out
            rate_currency = cheapest.currency
            rate_guests = cheapest.guests
            rate_availability = cheapest.availability_status
            rate_deep_link = sanitize_hotel_deep_link(
                cheapest.deep_link,
                provider=cheapest.provider,
            )
        else:
            # External mapping/provider failures are explicit skips. They do
            # not create a current snapshot or mutate the tracked offer.
            continue

        db.refresh(offer)
        if (
            not offer.is_active
            or _lifecycle_state_for_offer(offer) != _TRACKING_LIFECYCLE_ACTIVE
        ):
            provider_fetch_skipped += 1
            _sync_outcomes()
            continue

        # Determine previous price for delta tracking
        previous_snapshot = db.scalars(
            select(HotelRateSnapshot)
            .where(HotelRateSnapshot.tracked_offer_id == offer.id)
            .order_by(desc(HotelRateSnapshot.collected_at), desc(HotelRateSnapshot.id))
            .limit(1)
        ).first()

        previous_price: float | None = None
        if previous_snapshot is not None:
            previous_price = float(previous_snapshot.amount)

        # Close the lease with a conditional token update before adding the
        # snapshot. The update and subsequent insert share the caller's
        # transaction; if the token is stale, nothing is persisted.
        if query_lease is not None and not HotelSweepLeaseStore(db).finish(
            query_lease,
            status="done",
            now=utc_now_naive(),
            provider_run_id=provider_run_id,
            commit=False,
        ):
            provider_fetch_skipped += 1
            _sync_outcomes()
            continue

        # Create a new snapshot linked to this tracked offer
        new_snapshot = HotelRateSnapshot(
            hotel_id=offer.hotel_id,
            tracked_offer_id=offer.id,
            provider_run_id=provider_run_id,
            provider=rate_provider,
            check_in=rate_check_in,
            check_out=rate_check_out,
            guests=rate_guests,
            room_label=rate_room,
            meal_plan=rate_meal,
            cancellation_policy=rate_cancellation,
            currency=rate_currency,
            amount=rate_amount,
            availability_status=rate_availability,
            deep_link=rate_deep_link,
        )
        db.add(new_snapshot)
        snapshots_created += 1
        _sync_outcomes()

        # Sold-out observations remain useful availability evidence, but their
        # amount is not an eligible current price and must not overwrite the
        # tracked offer or create a price alert.
        new_price = rate_amount
        price_is_eligible = rate_availability not in {"unavailable", "stale"}
        if price_is_eligible:
            offer.current_price = new_price
            db.add(offer)

        # Create alert event if price changed from previous. This legacy
        # tracking signal remains persisted for history, but now carries the
        # same auditable identity metadata as rule-backed events.
        hotel = db.get(HotelProperty, offer.hotel_id)
        hotel_name = hotel.canonical_name if hotel else offer.hotel_id

        if (
            price_is_eligible
            and previous_snapshot is not None
            and previous_price is not None
            and previous_price != new_price
        ):
            delta = new_price - previous_price
            pct = round((delta / previous_price) * 100, 1) if previous_price > 0 else 0.0
            direction = t("es", "hotels.direction.rose") if delta > 0 else t("es", "hotels.direction.dropped")
            event_type = "price_above" if delta > 0 else "price_below"

            db.flush()
            raw_fingerprint = hashlib.sha256(
                "|".join(
                    str(value)
                    for value in (
                        offer.user_id,
                        offer.id,
                        event_type,
                        previous_snapshot.id,
                        new_snapshot.id,
                        round(new_price, 2),
                        offer.currency or "EUR",
                    )
                ).encode("utf-8")
            ).hexdigest()
            db.add(
            HotelAlertEvent(
                user_id=offer.user_id,
                rule_id=None,
                hotel_id=offer.hotel_id,
                    provider_run_id=provider_run_id,
                    event_type=event_type,
                    message=t(
                        "es",
                        "hotels.message.sweep_direction",
                        hotel=hotel_name,
                        direction=direction,
                        previous=f"{previous_price:.2f}",
                        current=f"{new_price:.2f}",
                        currency=offer.currency or "EUR",
                        pct=f"{pct:+.1f}%",
                    ),
                    trigger_value=new_price,
                    event_fingerprint=raw_fingerprint,
                    snapshot_before_id=previous_snapshot.id,
                    snapshot_after_id=new_snapshot.id,
                    comparability_key=_hotel_alert_comparability_key(
                        new_snapshot,
                        previous_snapshot,
                        hotel_id=offer.hotel_id,
                    ),
                    eligibility_status="not_evaluable",
                    reason_code="legacy_tracking_price_change",
                    evaluation_state="legacy_observation",
                    rule_version=_HOTEL_ALERT_RULE_VERSION,
                )
            )
    _sync_outcomes()
    if snapshots_created > 0:
        db.flush()

    return {
        "offers_scanned": offers_scanned,
        "snapshots_created": snapshots_created,
        "provider_fetch_attempted": provider_fetch_attempted,
        "provider_fetch_completed": provider_fetch_completed,
        "provider_fetch_empty": provider_fetch_empty,
        "provider_fetch_failed": provider_fetch_failed,
        "provider_fetch_skipped": provider_fetch_skipped,
        "provider_fetch_budget_denied": provider_fetch_budget_denied,
        **profile_error_counts,
    }


_HOTEL_ALERT_RULE_VERSION = "hotel-alert-v1"
_HOTEL_ALERT_INELIGIBLE_STATUSES = frozenset({"unavailable", "stale", "provider_error", "fixture"})


def _hotel_alert_snapshots_comparable(
    left: HotelRateSnapshot,
    right: HotelRateSnapshot,
) -> bool:
    """Return whether two snapshots describe the same comparable stay.

    Provider is intentionally excluded: ``provider_changed`` needs to compare
    the same stay across providers. Monetary and percentage rules still require
    the remaining identity fields to match exactly.
    """
    return (
        left.hotel_id == right.hotel_id
        and left.check_in == right.check_in
        and left.check_out == right.check_out
        and left.guests == right.guests
        and left.currency == right.currency
        and left.room_label == right.room_label
        and left.meal_plan == right.meal_plan
        and left.cancellation_policy == right.cancellation_policy
    )


def _hotel_alert_comparability_key(
    latest: HotelRateSnapshot | None,
    baseline: HotelRateSnapshot | None,
    *,
    hotel_id: str,
) -> str:
    if latest is None:
        return f"legacy:{hotel_id}"
    raw = "|".join(
        str(value)
        for value in (
            hotel_id,
            latest.check_in,
            latest.check_out,
            latest.guests,
            latest.currency,
            latest.room_label or "",
            latest.meal_plan or "",
            latest.cancellation_policy or "",
            baseline.currency if baseline is not None else "",
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rearm_hotel_alert_rule(rule: HotelAlertRule) -> None:
    """Reset transition memory after a rule observes a clear condition."""
    rule.evaluation_state = "rearmed" if rule.last_fired_at is not None else "clear"
    rule.last_fired_at = None
    rule.last_event_fingerprint = None


def _finalize_hotel_alert_candidates(
    db: Session,
    *,
    rule: HotelAlertRule,
    candidates: list[HotelAlertEvent],
    latest: HotelRateSnapshot | None,
    baseline: HotelRateSnapshot | None,
    previous: HotelRateSnapshot | None,
    now=None,
) -> list[HotelAlertEvent]:
    """Apply H26 fingerprint, rearming, cooldown and dedupe to candidates."""
    now = now or utc_now_naive()
    created: list[HotelAlertEvent] = []
    comparability_key = _hotel_alert_comparability_key(
        latest,
        baseline,
        hotel_id=rule.hotel_id,
    )
    baseline_id = baseline.id if baseline is not None else None
    for event in candidates:
        fingerprint_source = "|".join(
            str(value)
            for value in (
                rule.user_id,
                rule.id,
                rule.tracked_offer_id or "legacy_hotel_scope",
                rule.rule_type,
                _HOTEL_ALERT_RULE_VERSION,
                baseline_id or rule.compare_against,
                latest.id if latest is not None else "legacy-current",
                comparability_key,
                event.event_type,
                event.trigger_value,
            )
        )
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
        existing = db.scalar(
            select(HotelAlertEvent.id).where(HotelAlertEvent.event_fingerprint == fingerprint)
        )
        cooldown_until = (
            rule.last_fired_at + timedelta(minutes=max(1, rule.cooldown_minutes or 60))
            if rule.last_fired_at is not None
            else None
        )
        event.event_fingerprint = fingerprint
        event.snapshot_before_id = previous.id if previous is not None else None
        event.snapshot_after_id = latest.id if latest is not None else None
        event.baseline_snapshot_id = baseline_id
        event.baseline_source = rule.compare_against
        if baseline is not None:
            event.baseline_amount = float(baseline.amount)
            event.baseline_currency = baseline.currency
        elif rule.compare_against == "initial_price":
            tracked_offer = db.get(HotelTrackedOffer, rule.tracked_offer_id) if rule.tracked_offer_id else None
            if tracked_offer is not None and tracked_offer.initial_price is not None:
                event.baseline_amount = float(tracked_offer.initial_price)
                event.baseline_currency = tracked_offer.currency
        event.comparability_key = comparability_key
        event.reason_code = {
            "price_below": "price_below_threshold",
            "price_above": "price_above_threshold",
            "percentage_drop": "percentage_drop_threshold",
            "percentage_increase": "percentage_increase_threshold",
            "provider_changed": "provider_changed",
            "availability_returned": "availability_returned",
            "parity_break": "parity_break",
        }.get(event.event_type, event.event_type)
        event.eligibility_status = "triggered"
        event.evaluation_state = "fired"
        event.rule_version = _HOTEL_ALERT_RULE_VERSION
        event.cooldown_until = cooldown_until

        # A condition that remains true is one transition, even when a new
        # snapshot changes its fingerprint. Only a clear evaluation rearms it.
        if rule.evaluation_state in {"fired", "suppressed"}:
            rule.evaluation_state = "suppressed"
            continue
        if existing is not None or rule.last_event_fingerprint == fingerprint:
            rule.evaluation_state = "suppressed"
            continue
        if cooldown_until is not None and now < cooldown_until:
            rule.evaluation_state = "suppressed"
            continue

        rule.evaluation_state = "fired"
        rule.last_fired_at = now
        rule.last_event_fingerprint = fingerprint
        event.cooldown_until = now + timedelta(minutes=max(1, rule.cooldown_minutes or 60))
        created.append(event)
    return created


def evaluate_hotel_alerts(db: Session, *, provider_run_id: str) -> list[HotelAlertEvent]:
    rules = list(db.scalars(select(HotelAlertRule).where(HotelAlertRule.is_active.is_(True))))
    events: list[HotelAlertEvent] = []

    for rule in rules:
        hotel = db.get(HotelProperty, rule.hotel_id)
        hotel_name = hotel.canonical_name if hotel else rule.hotel_id

        # For tracked offer alerts, use tracked offer snapshots
        if rule.tracked_offer_id is not None and rule.rule_type in {
            "price_below", "price_above", "percentage_drop", "percentage_increase",
            "provider_changed", "availability_returned",
        }:
            tracked_offer = db.get(HotelTrackedOffer, rule.tracked_offer_id)
            if (
                tracked_offer is None
                or not tracked_offer.is_active
                or _lifecycle_state_for_offer(tracked_offer) != _TRACKING_LIFECYCLE_ACTIVE
            ):
                continue
            snapshots = list_tracked_offer_snapshots(
                db, user_id=tracked_offer.user_id, tracked_offer_id=tracked_offer.id
            )
            if not snapshots:
                _rearm_hotel_alert_rule(rule)
                continue
            before_count = len(events)
            _evaluate_tracked_alert_rule(
                db, rule, snapshots, hotel_name, provider_run_id, events
            )
            candidates = events[before_count:]
            del events[before_count:]
            latest_snapshot = snapshots[0] if snapshots else None
            previous_snapshot = snapshots[1] if len(snapshots) > 1 else None
            # ``initial_price`` is a user value, not necessarily an existing
            # snapshot. Keep its source auditable without inventing a snapshot
            # identity that the evaluator did not use.
            baseline_snapshot = None if rule.compare_against == "initial_price" else previous_snapshot
            if not candidates:
                _rearm_hotel_alert_rule(rule)
            events.extend(
                _finalize_hotel_alert_candidates(
                    db,
                    rule=rule,
                    candidates=candidates,
                    latest=latest_snapshot,
                    baseline=baseline_snapshot,
                    previous=previous_snapshot,
                )
            )
            continue

        # Legacy: evaluate only eligible prices. Sold-out rows remain visible
        # through the rates/history surface but cannot trigger monetary rules.
        rates = [
            rate
            for rate in list_hotel_rates(db, hotel_id=rule.hotel_id, check_in=None, check_out=None)
            if rate.availability_status not in {"unavailable", "stale"}
        ]
        if not rates:
            _rearm_hotel_alert_rule(rule)
            continue

        legacy_condition_triggered = False
        threshold_percent = rule.threshold_percent
        if rule.rule_type == "price_below":
            amounts_f = [float(r.amount) for r in rates]
            avg = sum(amounts_f) / len(amounts_f) if threshold_percent is not None and amounts_f else None
            for rate in rates:
                triggered = False
                trigger_value = None
                rate_f = float(rate.amount)
                if rule.threshold_amount is not None and rate_f < float(rule.threshold_amount):
                    triggered = True
                    trigger_value = rate_f
                if avg is not None and avg > 0 and threshold_percent is not None and ((avg - rate_f) / avg * 100) >= float(threshold_percent):
                    triggered = True
                    trigger_value = rate_f
                if triggered:
                    legacy_condition_triggered = True
                    candidate = HotelAlertEvent(
                        user_id=rule.user_id,
                        rule_id=rule.id,
                        hotel_id=rule.hotel_id,
                        provider_run_id=provider_run_id,
                        event_type="price_below",
                        message=f"{hotel_name}: {rate.provider} @ {rate.currency} {rate.amount:.2f}",
                        trigger_value=trigger_value,
                    )
                    events.extend(
                        _finalize_hotel_alert_candidates(
                            db,
                            rule=rule,
                            candidates=[candidate],
                            latest=rate,
                            baseline=None,
                            previous=None,
                        )
                    )
                    break

        elif rule.rule_type == "price_above":
            amounts_f = [float(r.amount) for r in rates]
            avg = sum(amounts_f) / len(amounts_f) if threshold_percent is not None and amounts_f else None
            for rate in rates:
                triggered = False
                trigger_value = None
                rate_f = float(rate.amount)
                if rule.threshold_amount is not None and rate_f > float(rule.threshold_amount):
                    triggered = True
                    trigger_value = rate_f
                if avg is not None and avg > 0 and threshold_percent is not None and ((rate_f - avg) / avg * 100) >= float(threshold_percent):
                    triggered = True
                    trigger_value = rate_f
                if triggered:
                    legacy_condition_triggered = True
                    candidate = HotelAlertEvent(
                        user_id=rule.user_id,
                        rule_id=rule.id,
                        hotel_id=rule.hotel_id,
                        provider_run_id=provider_run_id,
                        event_type="price_above",
                        message=f"{hotel_name}: {rate.provider} @ {rate.currency} {rate.amount:.2f}",
                        trigger_value=trigger_value,
                    )
                    events.extend(
                        _finalize_hotel_alert_candidates(
                            db,
                            rule=rule,
                            candidates=[candidate],
                            latest=rate,
                            baseline=None,
                            previous=None,
                        )
                    )
                    break

        elif rule.rule_type == "parity_break":
            signals = HotelParityService.compute_parity(rates)
            for signal in signals:
                if signal.is_parity_broken and signal.spread_percent is not None and (rule.threshold_percent is None or signal.spread_percent >= rule.threshold_percent):
                    legacy_condition_triggered = True
                    events.append(
                        HotelAlertEvent(
                            user_id=rule.user_id,
                            rule_id=rule.id,
                            hotel_id=rule.hotel_id,
                            provider_run_id=provider_run_id,
                            event_type="parity_break",
                            message=f"{hotel_name}: spread {signal.spread_percent}% ({signal.lowest_price}-{signal.highest_price} {signal.currency})",
                            trigger_value=signal.spread_percent,
                        )
                    )
                    break

        # New human rule types for non-tracked offers (fallback to legacy behavior)
        elif rule.rule_type == "percentage_drop":
            before_legacy = len(events)
            _evaluate_legacy_percentage_rule(db, rule, rates, hotel_name, provider_run_id, events, direction="drop")
            legacy_condition_triggered = len(events) > before_legacy
        elif rule.rule_type == "percentage_increase":
            before_legacy = len(events)
            _evaluate_legacy_percentage_rule(db, rule, rates, hotel_name, provider_run_id, events, direction="increase")
            legacy_condition_triggered = len(events) > before_legacy

        if not legacy_condition_triggered:
            _rearm_hotel_alert_rule(rule)

    # Legacy hotel-scope branches predate the H26 metadata path. Finalize
    # their candidates here so they receive the same stable fingerprint and
    # cooldown semantics without changing their V1 response shape.
    finalized_events: list[HotelAlertEvent] = []
    for event in events:
        if event.event_fingerprint is not None or event.rule_id is None:
            finalized_events.append(event)
            continue
        event_rule = db.get(HotelAlertRule, event.rule_id)
        if event_rule is None:
            finalized_events.append(event)
            continue
        finalized_events.extend(
            _finalize_hotel_alert_candidates(
                db,
                rule=event_rule,
                candidates=[event],
                latest=None,
                baseline=None,
                previous=None,
            )
        )
    events = finalized_events

    persisted_events: list[HotelAlertEvent] = []
    for event in events:
        try:
            with db.begin_nested():
                db.add(event)
                db.flush()
        except IntegrityError:
            # Concurrent evaluators can race between the fingerprint lookup and
            # insert. The unique index is authoritative; keep the first event.
            continue
        persisted_events.append(event)
    events = persisted_events

    if events:
        db.flush()
        provider_run = db.get(HotelProviderRun, provider_run_id)
        record_hotel_daily_metric(
            db,
            metric_name=METRIC_ALERT_EVENT,
            provider=provider_run.provider if provider_run else "unknown",
            outcome="created",
            increment=len(events),
        )
        for event in events:
            logger.info(
                "hotel_alert_created",
                extra={
                    "hotel_alert_event_id": event.id,
                    "hotel_provider_run_id": event.provider_run_id,
                    "hotel_correlation_id": provider_run.correlation_id if provider_run else None,
                    "client_event_id": provider_run.client_event_id if provider_run else None,
                },
            )

    return events


def _evaluate_tracked_alert_rule(
    db: Session,
    rule: HotelAlertRule,
    snapshots: list[HotelRateSnapshot],
    hotel_name: str,
    provider_run_id: str,
    events: list[HotelAlertEvent],
) -> None:
    """Evaluate a tracked-offer alert rule against its snapshots."""
    latest = snapshots[0]
    if latest.availability_status in {"unavailable", "stale"} and rule.rule_type in {
        "price_below",
        "price_above",
        "percentage_drop",
        "percentage_increase",
    }:
        return
    latest_amount = float(latest.amount)
    previous: HotelRateSnapshot | None = None
    for candidate in snapshots[1:]:
        if candidate.availability_status in _HOTEL_ALERT_INELIGIBLE_STATUSES:
            continue
        if _hotel_alert_snapshots_comparable(latest, candidate):
            previous = candidate
            break

    # Determine the comparison baseline based on compare_against
    compare_baseline: float | None = None
    if rule.compare_against == "initial_price":
        tracked_offer = db.get(HotelTrackedOffer, rule.tracked_offer_id) if rule.tracked_offer_id else None
        if tracked_offer is not None and tracked_offer.initial_price is not None:
            compare_baseline = float(tracked_offer.initial_price)
    elif previous is not None:
        compare_baseline = float(previous.amount)

    if rule.rule_type == "price_below":
        amount_triggered = rule.threshold_amount is not None and latest_amount < float(rule.threshold_amount)
        percent_triggered = (
            rule.threshold_percent is not None
            and compare_baseline is not None
            and compare_baseline > 0
            and ((compare_baseline - latest_amount) / compare_baseline) * 100 >= float(rule.threshold_percent)
        )
        if amount_triggered or percent_triggered:
            events.append(
                HotelAlertEvent(
                    user_id=rule.user_id,
                    rule_id=rule.id,
                    hotel_id=rule.hotel_id,
                    provider_run_id=provider_run_id,
                    event_type="price_below",
                    message=t("es", "hotels.message.price_dropped_to", hotel=hotel_name, currency=latest.currency, amount=f"{latest_amount:.2f}"),
                    trigger_value=latest_amount,
                )
            )

    elif rule.rule_type == "price_above":
        amount_triggered = rule.threshold_amount is not None and latest_amount > float(rule.threshold_amount)
        percent_triggered = (
            rule.threshold_percent is not None
            and compare_baseline is not None
            and compare_baseline > 0
            and ((latest_amount - compare_baseline) / compare_baseline) * 100 >= float(rule.threshold_percent)
        )
        if amount_triggered or percent_triggered:
            events.append(
                HotelAlertEvent(
                    user_id=rule.user_id,
                    rule_id=rule.id,
                    hotel_id=rule.hotel_id,
                    provider_run_id=provider_run_id,
                    event_type="price_above",
                    message=t("es", "hotels.message.price_rose_to", hotel=hotel_name, currency=latest.currency, amount=f"{latest_amount:.2f}"),
                    trigger_value=latest_amount,
                )
            )

    elif rule.rule_type == "percentage_drop" and compare_baseline is not None:
        if compare_baseline > 0:
            pct = ((compare_baseline - latest_amount) / compare_baseline) * 100
            if rule.threshold_percent is not None and pct >= float(rule.threshold_percent):
                events.append(
                    HotelAlertEvent(
                        user_id=rule.user_id,
                        rule_id=rule.id,
                        hotel_id=rule.hotel_id,
                        provider_run_id=provider_run_id,
                        event_type="percentage_drop",
                        message=t("es", "hotels.message.percentage_drop", hotel=hotel_name, pct=f"{pct:.1f}%", baseline=f"{compare_baseline:.2f}", current=f"{latest_amount:.2f}", currency=latest.currency),
                        trigger_value=pct,
                    )
                )

    elif rule.rule_type == "percentage_increase" and compare_baseline is not None:
        if compare_baseline > 0:
            pct = ((latest_amount - compare_baseline) / compare_baseline) * 100
            if rule.threshold_percent is not None and pct >= float(rule.threshold_percent):
                events.append(
                    HotelAlertEvent(
                        user_id=rule.user_id,
                        rule_id=rule.id,
                        hotel_id=rule.hotel_id,
                        provider_run_id=provider_run_id,
                        event_type="percentage_increase",
                        message=t("es", "hotels.message.percentage_increase", hotel=hotel_name, pct=f"{pct:.1f}%", baseline=f"{compare_baseline:.2f}", current=f"{latest_amount:.2f}", currency=latest.currency),
                        trigger_value=pct,
                    )
                )

    elif rule.rule_type == "provider_changed" and previous is not None:
        if latest.provider != previous.provider:
            events.append(
                HotelAlertEvent(
                    user_id=rule.user_id,
                    rule_id=rule.id,
                    hotel_id=rule.hotel_id,
                    provider_run_id=provider_run_id,
                    event_type="provider_changed",
                    message=t("es", "hotels.message.provider_changed", hotel=hotel_name, previous_provider=previous.provider or "?", current_provider=latest.provider or "?"),
                    trigger_value=latest_amount,
                )
            )

    elif rule.rule_type == "availability_returned" and previous is not None and previous.availability_status in {"unavailable", "stale"} and latest.availability_status == "available":
        events.append(
            HotelAlertEvent(
                user_id=rule.user_id,
                rule_id=rule.id,
                hotel_id=rule.hotel_id,
                provider_run_id=provider_run_id,
                event_type="availability_returned",
                message=t("es", "hotels.message.availability_returned", hotel=hotel_name, currency=latest.currency, amount=f"{latest_amount:.2f}"),
                trigger_value=latest_amount,
            )
        )


def _evaluate_legacy_percentage_rule(
    db: Session,
    rule: HotelAlertRule,
    rates: list[HotelRateSnapshot],
    hotel_name: str,
    provider_run_id: str,
    events: list[HotelAlertEvent],
    direction: str,
) -> None:
    """Legacy percentage rule evaluation against general hotel rates."""
    if not rates:
        return
    amounts = sorted(float(r.amount) for r in rates)
    lowest = amounts[0]
    for rate in rates:
        rate_f = float(rate.amount)
        if direction == "drop":
            baseline = max(amounts) if len(amounts) > 1 else lowest
            if baseline > 0:
                pct = ((baseline - rate_f) / baseline) * 100
                if rule.threshold_percent is not None and pct >= float(rule.threshold_percent):
                    events.append(
                        HotelAlertEvent(
                            user_id=rule.user_id,
                            rule_id=rule.id,
                            hotel_id=rule.hotel_id,
                            provider_run_id=provider_run_id,
                            event_type="percentage_drop",
                            message=f"{hotel_name}: spread {pct:.1f}% ({rate.currency} {rate.amount:.2f})",
                            trigger_value=pct,
                        )
                    )
                    break
        else:
            baseline = lowest
            if baseline > 0:
                pct = ((rate_f - baseline) / baseline) * 100
                if rule.threshold_percent is not None and pct >= float(rule.threshold_percent):
                    events.append(
                        HotelAlertEvent(
                            user_id=rule.user_id,
                            rule_id=rule.id,
                            hotel_id=rule.hotel_id,
                            provider_run_id=provider_run_id,
                            event_type="percentage_increase",
                            message=f"{hotel_name}: spread {pct:.1f}% ({rate.currency} {rate.amount:.2f})",
                            trigger_value=pct,
                        )
                    )
                    break


def list_hotel_alert_events(
    db: Session,
    *,
    user_id: str,
    hotel_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[HotelAlertEvent]:
    # New events are private by user_id. During migration, historical events
    # linked to an owned rule remain attributable; events without either
    # ownership or a rule are intentionally excluded.
    historical_rule_owner = select(HotelAlertRule.id).where(
        HotelAlertRule.id == HotelAlertEvent.rule_id,
        HotelAlertRule.user_id == user_id,
    )
    stmt = select(HotelAlertEvent).where(
        (
            (HotelAlertEvent.user_id == user_id)
            & or_(
                HotelAlertEvent.evaluation_state.is_(None),
                HotelAlertEvent.evaluation_state != "legacy_observation",
            )
        )
        | ((HotelAlertEvent.user_id.is_(None)) & historical_rule_owner.exists())
    )
    if hotel_id is not None:
        stmt = stmt.where(HotelAlertEvent.hotel_id == hotel_id)
    stmt = stmt.order_by(desc(HotelAlertEvent.created_at), desc(HotelAlertEvent.id)).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def create_hotel_delivery_intent(
    db: Session,
    *,
    event_id: str,
    user_id: str,
    channel: str = "in_app",
    template_version: str = "hotel-alert-v1",
) -> HotelNotificationDelivery | None:
    """Create an idempotent in-app delivery intent for an owned event."""
    if channel != "in_app":
        return None
    event = db.scalar(select(HotelAlertEvent).where(HotelAlertEvent.id == event_id))
    if event is None or event.user_id != user_id or event.user_id is None:
        return None
    if event.evaluation_state == "legacy_observation":
        # Raw sweep observations are history/telemetry only; old rule-less
        # tracking events remain compatible when they have no marker.
        return None
    if event.rule_id is not None:
        owned_rule = db.scalar(
            select(HotelAlertRule).where(
                HotelAlertRule.id == event.rule_id,
                HotelAlertRule.user_id == user_id,
            )
        )
        if owned_rule is None:
            return None
        if owned_rule.tracked_offer_id is not None:
            tracked_offer = db.get(HotelTrackedOffer, owned_rule.tracked_offer_id)
            if (
                tracked_offer is None
                or not tracked_offer.is_active
                or _lifecycle_state_for_offer(tracked_offer) != _TRACKING_LIFECYCLE_ACTIVE
            ):
                return None

    idempotency_key = hashlib.sha256(
        f"{event.id}:{user_id}:{channel}:{template_version}".encode("utf-8")
    ).hexdigest()
    existing = db.scalar(
        select(HotelNotificationDelivery).where(
            HotelNotificationDelivery.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        setattr(existing, "_created_by_call", False)
        return existing

    delivery = HotelNotificationDelivery(
        source_event_id=event.id,
        recipient_user_id=user_id,
        channel=channel,
        template_version=template_version,
        idempotency_key=idempotency_key,
        status="queued",
        next_attempt_at=utc_now_naive(),
    )
    db.add(delivery)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        existing_after_conflict = db.scalar(
            select(HotelNotificationDelivery).where(
                HotelNotificationDelivery.idempotency_key == idempotency_key
            )
        )
        if existing_after_conflict is not None:
            setattr(existing_after_conflict, "_created_by_call", False)
        return existing_after_conflict
    setattr(delivery, "_created_by_call", True)
    return delivery


def materialize_hotel_delivery_intents(
    db: Session,
    *,
    provider_run_id: str,
) -> int:
    """Queue owned hotel events from one run without crossing users."""
    events = list(
        db.scalars(
            select(HotelAlertEvent).where(
                HotelAlertEvent.provider_run_id == provider_run_id,
                HotelAlertEvent.user_id.is_not(None),
                or_(
                    HotelAlertEvent.evaluation_state.is_(None),
                    HotelAlertEvent.evaluation_state != "legacy_observation",
                ),
            )
        )
    )
    created = 0
    for event in events:
        existing = db.scalar(
            select(HotelNotificationDelivery.id).where(
                HotelNotificationDelivery.source_event_id == event.id,
                HotelNotificationDelivery.channel == "in_app",
            )
        )
        delivery = create_hotel_delivery_intent(
            db,
            event_id=event.id,
            user_id=event.user_id or "",
        )
        if delivery is not None and existing is None and getattr(delivery, "_created_by_call", False):
            created += 1
    return created


def get_hotel_alert_trace(
    db: Session,
    *,
    user_id: str,
    event_id: str,
) -> HotelAlertTrace | None:
    """Resolve alert intent through the owned event's provider run.

    This is deliberately an internal observability projection: it returns only
    opaque trace identifiers, never the alert payload, and requires event
    ownership. Legacy events remain resolvable when their rule belongs to the
    user, but events that rely on a shared ``hotel_id`` alone are not visible.
    """
    historical_rule_owner = select(HotelAlertRule.id).where(
        HotelAlertRule.id == HotelAlertEvent.rule_id,
        HotelAlertRule.user_id == user_id,
    )
    row = db.execute(
        select(HotelAlertEvent, HotelProviderRun)
        .outerjoin(
            HotelProviderRun,
            HotelProviderRun.id == HotelAlertEvent.provider_run_id,
        )
        .where(
            HotelAlertEvent.id == event_id,
            or_(
                HotelAlertEvent.user_id == user_id,
                and_(
                    HotelAlertEvent.user_id.is_(None),
                    HotelAlertEvent.rule_id.is_not(None),
                    historical_rule_owner.exists(),
                ),
            ),
        )
    ).first()
    if row is None:
        return None

    event, provider_run = row
    return HotelAlertTrace(
        event_id=event.id,
        provider_run_id=event.provider_run_id,
        correlation_id=provider_run.correlation_id if provider_run else None,
        client_event_id=provider_run.client_event_id if provider_run else None,
    )


# ── HotelTrackedOffer ──────────────────────────────────────────────


def _validate_tracked_offer_context(
    *,
    check_in: Date | None,
    check_out: Date | None,
    guests: int | None,
) -> None:
    if (check_in is None) != (check_out is None):
        raise ValueError("tracked_offer_dates_required_together")
    if check_in is not None and check_out is not None and check_out <= check_in:
        raise ValueError("invalid_date_range")
    if guests is not None and guests < 1:
        raise ValueError("tracked_offer_guests_invalid")


def create_tracked_offer(
    db: Session,
    *,
    user_id: str,
    hotel_id: str,
    area_label: str | None = None,
    origin_query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: int | None = None,
    check_in: Date | None = None,
    check_out: Date | None = None,
    guests: int = 2,
    room_label: str | None = None,
    meal_plan: str | None = None,
    cancellation_policy: str | None = None,
    provider: str = "mock",
    initial_price: float | None = None,
    current_price: float | None = None,
    target_price: float | None = None,
    currency: str = "EUR",
) -> HotelTrackedOffer:
    _ = get_hotel_or_404(db, hotel_id)
    _validate_tracked_offer_context(
        check_in=check_in,
        check_out=check_out,
        guests=guests,
    )
    if check_in is not None and check_out is not None:
        identity_values = {
            "user_id": user_id,
            "hotel_id": hotel_id,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "provider": provider,
        }
        existing_stmt = select(HotelTrackedOffer)
        for field_name, value in identity_values.items():
            column = getattr(HotelTrackedOffer, field_name)
            existing_stmt = existing_stmt.where(column.is_(None) if value is None else column == value)
        if db.scalar(existing_stmt) is not None:
            raise ValueError("tracked_offer_already_exists")

    current: float | None
    if initial_price is not None:
        current = current_price if current_price is not None else initial_price
    else:
        current = current_price

    offer = HotelTrackedOffer(
        user_id=user_id,
        hotel_id=hotel_id,
        area_label=area_label,
        origin_query=origin_query,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        room_label=room_label,
        meal_plan=meal_plan,
        cancellation_policy=cancellation_policy,
        provider=provider,
        initial_price=initial_price,
        current_price=current,
        target_price=target_price,
        currency=currency,
    )
    db.add(offer)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("tracked_offer_already_exists") from exc

    snapshot = None
    if check_in is not None and check_out is not None and current is not None:
        snapshot = HotelRateSnapshot(
            hotel_id=hotel_id,
            tracked_offer_id=offer.id,
            provider=provider,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            room_label=room_label,
            meal_plan=meal_plan,
            cancellation_policy=cancellation_policy,
            currency=currency,
            amount=current,
            availability_status="available",
        )
        db.add(snapshot)

    if is_hotel_canonical_dual_write_enabled():
        canonical_stay_offer = write_canonical_tracking_watch(db, tracked_offer=offer)
        if snapshot is not None and canonical_stay_offer is not None:
            snapshot.stay_offer_id = canonical_stay_offer.id
            snapshot.stay_query_fingerprint = canonical_stay_offer.stay_query_fingerprint
            snapshot.offer_fingerprint = canonical_stay_offer.offer_fingerprint
            snapshot.snapshot_outcome = "success"
            snapshot.price_semantics = "unknown"
            snapshot.conditions_completeness = "unknown"

    db.commit()
    db.refresh(offer)
    return offer


def list_tracked_offers(
    db: Session,
    *,
    user_id: str,
    is_active: bool | None = None,
) -> list[HotelTrackedOffer]:
    stmt = select(HotelTrackedOffer).where(HotelTrackedOffer.user_id == user_id)
    if is_active is not None:
        stmt = stmt.where(HotelTrackedOffer.is_active == is_active)
    stmt = stmt.order_by(desc(HotelTrackedOffer.created_at), desc(HotelTrackedOffer.id))
    return list(db.scalars(stmt))


_TRACKING_LIFECYCLE_ACTIVE = "active"
_TRACKING_LIFECYCLE_PAUSED = "paused"
_TRACKING_LIFECYCLE_EXPIRED = "expired"
_TRACKING_LIFECYCLE_ARCHIVED = "archived"


def _lifecycle_state_for_offer(offer: HotelTrackedOffer) -> str:
    if offer.lifecycle_state:
        return offer.lifecycle_state
    return _TRACKING_LIFECYCLE_ACTIVE if offer.is_active else _TRACKING_LIFECYCLE_PAUSED


def _suppress_pending_tracked_offer_deliveries(db: Session, *, tracked_offer_id: str) -> None:
    rule_ids = select(HotelAlertRule.id).where(HotelAlertRule.tracked_offer_id == tracked_offer_id)
    event_ids = select(HotelAlertEvent.id).where(HotelAlertEvent.rule_id.in_(rule_ids))
    db.execute(
        update(HotelNotificationDelivery)
        .where(
            HotelNotificationDelivery.source_event_id.in_(event_ids),
            HotelNotificationDelivery.status == "queued",
        )
        .values(
            status="suppressed",
            next_attempt_at=None,
            last_error="tracking_lifecycle_suppressed",
            error_class="permanent",
        )
    )


def transition_tracked_offer_lifecycle(
    db: Session,
    *,
    user_id: str,
    tracked_offer_id: str,
    action: str,
    expected_state_version: int,
    source: str = "v2_api",
    today: Date | None = None,
    commit: bool = True,
) -> HotelTrackedOfferLifecycleTransition:
    offer = get_tracked_offer_or_404(db, user_id=user_id, tracked_offer_id=tracked_offer_id)
    current_state = _lifecycle_state_for_offer(offer)
    current_version = offer.lifecycle_version or 1
    if expected_state_version != current_version:
        raise ValueError("tracked_offer_state_conflict")

    lifecycle_today = today or utc_now_naive().date()
    if action == "pause":
        if current_state in {_TRACKING_LIFECYCLE_EXPIRED, _TRACKING_LIFECYCLE_ARCHIVED}:
            raise ValueError("tracked_offer_lifecycle_not_pausable")
        target_state = _TRACKING_LIFECYCLE_PAUSED
        target_is_active = False
        outcome = "applied"
    elif action == "resume":
        if current_state in {_TRACKING_LIFECYCLE_EXPIRED, _TRACKING_LIFECYCLE_ARCHIVED}:
            raise ValueError("tracked_offer_lifecycle_not_resumable")
        if offer.check_in is None or offer.check_out is None:
            raise ValueError("tracked_offer_resume_context_incomplete")
        if offer.check_out < lifecycle_today:
            target_state = _TRACKING_LIFECYCLE_EXPIRED
            target_is_active = False
            outcome = "expired"
        else:
            target_state = _TRACKING_LIFECYCLE_ACTIVE
            target_is_active = True
            outcome = "applied"
    elif action == "expire":
        target_state = _TRACKING_LIFECYCLE_EXPIRED
        target_is_active = False
        outcome = "expired"
    elif action == "archive":
        target_state = _TRACKING_LIFECYCLE_ARCHIVED
        target_is_active = False
        outcome = "applied"
    else:
        raise ValueError("invalid_tracked_offer_lifecycle_action")

    if current_state == target_state and offer.is_active == target_is_active:
        return HotelTrackedOfferLifecycleTransition(offer=offer, outcome="existing")

    changed_at = utc_now_naive()
    next_version = current_version + 1
    result = db.execute(
        update(HotelTrackedOffer)
        .where(
            HotelTrackedOffer.id == offer.id,
            HotelTrackedOffer.user_id == user_id,
            HotelTrackedOffer.lifecycle_version == current_version,
        )
        .values(
            lifecycle_state=target_state,
            lifecycle_version=next_version,
            lifecycle_changed_at=changed_at,
            is_active=target_is_active,
            updated_at=changed_at,
        )
    )
    assert isinstance(result, CursorResult)
    if result.rowcount != 1:
        db.rollback()
        raise ValueError("tracked_offer_state_conflict")

    db.add(
        HotelTrackedOfferLifecycleEvent(
            tracked_offer_id=offer.id,
            user_id=user_id,
            from_state=current_state,
            to_state=target_state,
            action=action,
            source=source,
            state_version=next_version,
            created_at=changed_at,
        )
    )
    if target_state in {
        _TRACKING_LIFECYCLE_PAUSED,
        _TRACKING_LIFECYCLE_EXPIRED,
        _TRACKING_LIFECYCLE_ARCHIVED,
    }:
        _suppress_pending_tracked_offer_deliveries(db, tracked_offer_id=offer.id)
    try:
        db.flush()
        if commit:
            db.commit()
    except IntegrityError as exc:
        if commit:
            db.rollback()
            raise ValueError("tracked_offer_state_conflict") from exc
        raise
    db.refresh(offer)
    return HotelTrackedOfferLifecycleTransition(offer=offer, outcome=outcome)


def expire_due_tracked_offers(db: Session, *, today: Date | None = None) -> int:
    # Stay dates are entered and displayed as local calendar dates, so expiry
    # must not lag by one local day while UTC is still on the previous date.
    lifecycle_today = today or Date.today()
    due_offers = list(
        db.scalars(
            select(HotelTrackedOffer).where(
                HotelTrackedOffer.check_out.is_not(None),
                HotelTrackedOffer.check_out < lifecycle_today,
                HotelTrackedOffer.lifecycle_state.in_(
                    (_TRACKING_LIFECYCLE_ACTIVE, _TRACKING_LIFECYCLE_PAUSED),
                ),
            )
        )
    )
    expired = 0
    for offer in due_offers:
        try:
            with db.begin_nested():
                transition = transition_tracked_offer_lifecycle(
                    db,
                    user_id=offer.user_id,
                    tracked_offer_id=offer.id,
                    action="expire",
                    expected_state_version=offer.lifecycle_version or 1,
                    source="sweep_expiration",
                    today=lifecycle_today,
                    commit=False,
                )
        except (IntegrityError, ValueError) as exc:
            if str(exc) == "tracked_offer_state_conflict":
                continue
            raise
        if transition.outcome == "expired":
            expired += 1
    return expired


def list_tracked_offer_statuses(
    db: Session,
    *,
    user_id: str,
    is_active: bool | None = None,
) -> list[HotelTrackedOfferStatus]:
    offers = list_tracked_offers(db, user_id=user_id, is_active=is_active)
    if not offers:
        return []

    offer_ids = [offer.id for offer in offers]
    snapshots = list(
        db.scalars(
            select(HotelRateSnapshot)
            .where(HotelRateSnapshot.tracked_offer_id.in_(offer_ids))
            .order_by(
                HotelRateSnapshot.tracked_offer_id,
                desc(HotelRateSnapshot.collected_at),
                desc(HotelRateSnapshot.id),
            )
        )
    )
    latest_by_offer_id: dict[str, HotelRateSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.tracked_offer_id is not None:
            latest_by_offer_id.setdefault(snapshot.tracked_offer_id, snapshot)

    projections: list[HotelTrackedOfferStatus] = []
    for offer in offers:
        latest_snapshot = latest_by_offer_id.get(offer.id)
        warning_codes: list[str] = []
        lifecycle_state = _lifecycle_state_for_offer(offer)
        if lifecycle_state == _TRACKING_LIFECYCLE_EXPIRED:
            state = "expired"
            warning_codes.append("tracking_expired")
        elif lifecycle_state == _TRACKING_LIFECYCLE_ARCHIVED:
            state = "archived"
            warning_codes.append("tracking_archived")
        elif not offer.is_active or lifecycle_state == _TRACKING_LIFECYCLE_PAUSED:
            state = "paused"
        elif offer.check_in is None or offer.check_out is None:
            state = "pending_context"
            warning_codes.append("tracking_context_incomplete")
        elif latest_snapshot is None:
            state = "pending_first_observation"
            warning_codes.append("initial_observation_missing")
        elif latest_snapshot.availability_status == "stale":
            state = "partial"
            warning_codes.append("observation_stale")
        elif latest_snapshot.availability_status not in {"available", "limited"}:
            state = "unavailable"
            warning_codes.append("observation_unavailable")
        else:
            is_v2_complete = (
                latest_snapshot.stay_offer_id is not None
                and latest_snapshot.price_semantics == "total"
                and latest_snapshot.amount_total is not None
                and latest_snapshot.conditions_completeness == "complete"
                and latest_snapshot.snapshot_outcome == "success"
                and latest_snapshot.availability_status in {"available", "limited"}
            )
            state = "active" if is_v2_complete else "partial"
            if latest_snapshot.stay_offer_id is None:
                warning_codes.append("legacy_tracking_contract")
            if latest_snapshot.price_semantics != "total":
                warning_codes.append("price_semantics_unknown")
            elif latest_snapshot.amount_total is None:
                warning_codes.append("price_total_missing")
            if latest_snapshot.conditions_completeness != "complete":
                warning_codes.append("conditions_incomplete")
            if latest_snapshot.snapshot_outcome != "success":
                warning_codes.append("observation_outcome_unverified")
        projections.append(
            HotelTrackedOfferStatus(
                offer=offer,
                latest_snapshot=latest_snapshot,
                state=state,
                warning_codes=tuple(warning_codes),
            )
        )
    return projections


def create_tracked_offer_from_v2_source_rate(
    db: Session,
    *,
    user_id: str,
    source_rate_id: str,
) -> HotelTrackedOfferCreation:
    source_rate = db.get(HotelRateSnapshot, source_rate_id)
    if source_rate is None or source_rate.tracked_offer_id is not None:
        raise ValueError("hotel_source_rate_not_found")
    if source_rate.stay_offer_id is None:
        raise ValueError("hotel_source_rate_not_eligible")
    stay_offer = db.get(HotelStayOffer, source_rate.stay_offer_id)
    if stay_offer is None:
        raise ValueError("hotel_source_rate_not_eligible")
    if (
        stay_offer.canonical_hotel_id != source_rate.hotel_id
        or stay_offer.provider != source_rate.provider
        or source_rate.stay_query_fingerprint != stay_offer.stay_query_fingerprint
        or source_rate.offer_fingerprint != stay_offer.offer_fingerprint
        or source_rate.snapshot_outcome != "success"
        or source_rate.price_semantics != "total"
        or source_rate.amount_total is None
        or source_rate.conditions_completeness != "complete"
        or source_rate.availability_status not in {"available", "limited"}
    ):
        raise ValueError("hotel_source_rate_not_eligible")

    existing_watch = db.scalar(
        select(HotelUserStayWatch).where(
            HotelUserStayWatch.user_id == user_id,
            HotelUserStayWatch.stay_offer_id == stay_offer.id,
        )
    )
    if existing_watch is not None:
        if existing_watch.legacy_tracked_offer_id is None:
            raise ValueError("canonical_tracking_watch_missing_legacy")
        existing_offer = db.get(HotelTrackedOffer, existing_watch.legacy_tracked_offer_id)
        if existing_offer is None:
            raise ValueError("canonical_tracking_watch_missing_legacy")
        return HotelTrackedOfferCreation(offer=existing_offer, created=False)

    offer = HotelTrackedOffer(
        user_id=user_id,
        hotel_id=source_rate.hotel_id,
        check_in=source_rate.check_in,
        check_out=source_rate.check_out,
        guests=source_rate.guests,
        room_label=source_rate.room_label,
        meal_plan=source_rate.meal_plan,
        cancellation_policy=source_rate.cancellation_policy,
        provider=source_rate.provider,
        offer_fingerprint=stay_offer.offer_fingerprint,
        initial_price=source_rate.amount_total,
        current_price=source_rate.amount_total,
        currency=source_rate.currency,
    )
    db.add(offer)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        existing_watch = db.scalar(
            select(HotelUserStayWatch).where(
                HotelUserStayWatch.user_id == user_id,
                HotelUserStayWatch.stay_offer_id == stay_offer.id,
            )
        )
        if existing_watch is not None and existing_watch.legacy_tracked_offer_id is not None:
            existing_offer = db.get(HotelTrackedOffer, existing_watch.legacy_tracked_offer_id)
            if existing_offer is not None:
                return HotelTrackedOfferCreation(offer=existing_offer, created=False)
        raise ValueError("tracked_offer_already_exists") from exc

    db.add(
        HotelRateSnapshot(
            hotel_id=source_rate.hotel_id,
            stay_offer_id=stay_offer.id,
            tracked_offer_id=offer.id,
            provider=source_rate.provider,
            check_in=source_rate.check_in,
            check_out=source_rate.check_out,
            guests=source_rate.guests,
            room_label=source_rate.room_label,
            meal_plan=source_rate.meal_plan,
            cancellation_policy=source_rate.cancellation_policy,
            currency=source_rate.currency,
            amount=source_rate.amount_total,
            availability_status=source_rate.availability_status,
            observed_at=source_rate.observed_at,
            stay_query_fingerprint=stay_offer.stay_query_fingerprint,
            offer_fingerprint=stay_offer.offer_fingerprint,
            snapshot_outcome="success",
            price_semantics="total",
            amount_base=source_rate.amount_base,
            amount_total=source_rate.amount_total,
            fees_json=source_rate.fees_json,
            conditions_completeness="complete",
        )
    )
    db.add(
        HotelUserStayWatch(
            user_id=user_id,
            stay_offer_id=stay_offer.id,
            legacy_tracked_offer_id=offer.id,
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_watch = db.scalar(
            select(HotelUserStayWatch).where(
                HotelUserStayWatch.user_id == user_id,
                HotelUserStayWatch.stay_offer_id == stay_offer.id,
            )
        )
        if existing_watch is not None and existing_watch.legacy_tracked_offer_id is not None:
            existing_offer = db.get(HotelTrackedOffer, existing_watch.legacy_tracked_offer_id)
            if existing_offer is not None:
                return HotelTrackedOfferCreation(offer=existing_offer, created=False)
        raise ValueError("tracked_offer_already_exists") from exc
    db.refresh(offer)
    return HotelTrackedOfferCreation(offer=offer, created=True)


def get_tracked_offer_or_404(db: Session, *, user_id: str, tracked_offer_id: str) -> HotelTrackedOffer:
    offer = db.get(HotelTrackedOffer, tracked_offer_id)
    if not offer:
        raise ValueError("tracked_offer_not_found")
    if offer.user_id != user_id:
        raise PermissionError("not_allowed")
    return offer


def update_tracked_offer(
    db: Session,
    *,
    user_id: str,
    tracked_offer_id: str,
    update_data: dict[str, object],
) -> HotelTrackedOffer:
    offer = get_tracked_offer_or_404(db, user_id=user_id, tracked_offer_id=tracked_offer_id)

    allowed = {
        "area_label",
        "origin_query",
        "latitude",
        "longitude",
        "radius_km",
        "check_in",
        "check_out",
        "guests",
        "room_label",
        "meal_plan",
        "cancellation_policy",
        "provider",
        "initial_price",
        "current_price",
        "target_price",
        "currency",
        "is_active",
    }

    identity_fields = {
        "check_in",
        "check_out",
        "guests",
        "provider",
        "room_label",
        "meal_plan",
        "cancellation_policy",
        "currency",
    }
    changed_identity_fields = {
        field
        for field, value in update_data.items()
        if field in identity_fields and value != getattr(offer, field)
    }
    if changed_identity_fields:
        raise ValueError("tracked_offer_identity_immutable")

    candidate_check_in = cast(Date | None, update_data.get("check_in", offer.check_in))
    candidate_check_out = cast(Date | None, update_data.get("check_out", offer.check_out))
    candidate_guests = cast(int | None, update_data.get("guests", offer.guests))
    _validate_tracked_offer_context(
        check_in=candidate_check_in,
        check_out=candidate_check_out,
        guests=candidate_guests,
    )

    if "is_active" in update_data:
        requested_is_active = update_data["is_active"]
        if isinstance(requested_is_active, bool) and requested_is_active != offer.is_active:
            transition = transition_tracked_offer_lifecycle(
                db,
                user_id=user_id,
                tracked_offer_id=tracked_offer_id,
                action="resume" if requested_is_active else "pause",
                expected_state_version=offer.lifecycle_version or 1,
                source="v1_bridge",
            )
            offer = transition.offer

    for field, value in update_data.items():
        if field in allowed and field != "is_active":
            setattr(offer, field, value)

    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def delete_tracked_offer(db: Session, *, user_id: str, tracked_offer_id: str) -> None:
    offer = get_tracked_offer_or_404(db, user_id=user_id, tracked_offer_id=tracked_offer_id)
    db.execute(
        delete(HotelTrackedOfferLifecycleEvent).where(
            HotelTrackedOfferLifecycleEvent.tracked_offer_id == offer.id,
        )
    )
    db.execute(
        delete(HotelUserStayWatch).where(
            HotelUserStayWatch.legacy_tracked_offer_id == offer.id,
        )
    )
    # Rate snapshots and alert rules created for a tracked offer are owned by
    # that offer. Delete them explicitly because the legacy FKs have no database
    # cascade and SQLite otherwise leaves dependent rows behind.
    db.execute(delete(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == offer.id))
    alert_rule_ids = select(HotelAlertRule.id).where(HotelAlertRule.tracked_offer_id == offer.id)
    db.execute(delete(HotelAlertEvent).where(HotelAlertEvent.rule_id.in_(alert_rule_ids)))
    db.execute(delete(HotelAlertRule).where(HotelAlertRule.tracked_offer_id == offer.id))
    db.delete(offer)
    db.commit()


def area_resolve(
    db: Session,
    *,
    q: str,
) -> HotelAreaResolveResult:
    normalized = HotelNormalizationService.normalize_text(q)

    # Find hotels whose normalized_city contains the query
    hotels = list(
        db.scalars(
            select(HotelProperty).where(
                HotelProperty.normalized_city.contains(normalized),
                HotelProperty.latitude.is_not(None),
                HotelProperty.longitude.is_not(None),
            )
        )
    )

    if not hotels:
        # Fallback to external geocoder if enabled
        from app.hotels.geocoder import geocode_city

        geocode_result = geocode_city(q)
        if geocode_result is not None:
            return cast(HotelAreaResolveResult, geocode_result)

        raise ValueError("area_not_found")

    # Compute centroid
    resolved_hotels: list[tuple[HotelProperty, float, float]] = []
    for hotel in hotels:
        hotel_latitude = hotel.latitude
        hotel_longitude = hotel.longitude
        if hotel_latitude is None or hotel_longitude is None:
            continue
        resolved_hotels.append((hotel, float(hotel_latitude), float(hotel_longitude)))
    if not resolved_hotels:
        raise ValueError("area_not_found")
    lats = [latitude for _, latitude, _ in resolved_hotels]
    lngs = [longitude for _, _, longitude in resolved_hotels]
    countries = {hotel.country_code for hotel, _, _ in resolved_hotels}

    avg_lat = sum(lats) / len(lats)
    avg_lng = sum(lngs) / len(lngs)

    # Determine confidence based on city convergence
    if len(resolved_hotels) >= 3:
        confidence = "high"
    elif len(resolved_hotels) == 1:
        confidence = "low"
    else:
        confidence = "medium"

    # Build area label from the most common city
    city_counts: dict[str, int] = {}
    for hotel, _, _ in resolved_hotels:
        city_counts[hotel.city] = city_counts.get(hotel.city, 0) + 1
    best_city = max(city_counts, key=city_counts.get)  # type: ignore[arg-type]

    country_code = countries.pop() if len(countries) == 1 else "ES"

    return {
        "area_label": best_city,
        "latitude": round(avg_lat, 4),
        "longitude": round(avg_lng, 4),
        "country_code": country_code,
        "confidence": confidence,
        "source": "internal",
    }


def area_search(
    db: Session,
    *,
    latitude: float,
    longitude: float,
    radius_km: int,
    check_in: Date,
    check_out: Date,
    guests: int,
    currency: str,
    min_stars: int | None = None,
    max_price: float | None = None,
    sort: str = "price",
    user_id: str | None = None,
    use_provider: bool = False,
    latency_sink: Callable[[ProviderLatencySample], None] | None = None,
    provider_state: dict[str, str] | None = None,
) -> list[HotelAreaSearchResult]:
    # Get all hotels with coordinates
    hotels = list(
        db.scalars(
            select(HotelProperty).where(
                HotelProperty.latitude.is_not(None),
                HotelProperty.longitude.is_not(None),
            )
        )
    )

    # Filter by radius and min_stars
    nearby: list[tuple[HotelProperty, float]] = []
    for hotel in hotels:
        if hotel.latitude is None or hotel.longitude is None:
            continue
        if min_stars is not None and (hotel.stars is None or hotel.stars < min_stars):
            continue
        distance = haversine_km(
            latitude, longitude,
            float(hotel.latitude), float(hotel.longitude),
        )
        if distance <= radius_km:
            nearby.append((hotel, round(distance, 1)))

    if not nearby:
        return []

    nearby_hotel_ids = [h.id for h, _ in nearby]

    # ── External provider rate fetching (Makcorps) ─────────────────
    provider_price_map: dict[str, HotelAreaPriceInfo] = {}
    provider_unavailable_hotel_ids: set[str] = set()
    if use_provider:
        provider_id: str | None = None
        try:
            from app.hotels.ingestion import resolve_hotel_provider

            activation = resolve_hotel_activation(operation="area_search")
            provider_id = activation.provider
            if not activation.feature_enabled or not activation.external_calls_allowed:
                logger.info("hotel_provider_search_blocked reason=%s", activation.reason)
                adapter = None
            else:
                adapter = resolve_hotel_provider(provider=activation.provider)
            if adapter is not None and hasattr(adapter, "fetch_hotel_rates") and hasattr(adapter, "provider_id"):
                failure_status = _fetch_and_store_provider_rates(
                    db=db,
                    adapter=adapter,
                    nearby_hotel_ids=nearby_hotel_ids,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    currency=currency,
                    provider_price_map=provider_price_map,
                    provider_unavailable_hotel_ids=provider_unavailable_hotel_ids,
                    latency_sink=latency_sink,
                )
                if failure_status is not None and provider_state is not None:
                    provider_state["provider"] = provider_id or activation.provider
                    provider_state["status"] = failure_status
        except Exception as exc:
            logger.warning("area_search provider fetch skipped: %s", exc)
            if provider_state is not None:
                provider_state["provider"] = provider_id or "unknown"
                provider_state["status"] = _provider_failure_status(exc)

    # Get cheapest rate per hotel for the given criteria (DB fallback)
    effective_price = case(
        (
            and_(
                HotelRateSnapshot.price_semantics == "total",
                HotelRateSnapshot.amount_total.is_not(None),
            ),
            HotelRateSnapshot.amount_total,
        ),
        else_=HotelRateSnapshot.amount,
    )
    rates_subq = (
        select(
            HotelRateSnapshot.hotel_id,
            HotelRateSnapshot.provider,
            HotelRateSnapshot.amount,
            HotelRateSnapshot.currency,
            HotelRateSnapshot.price_semantics,
            HotelRateSnapshot.amount_total,
            HotelRateSnapshot.observed_at,
            HotelRateSnapshot.snapshot_outcome,
            HotelRateSnapshot.conditions_completeness,
            func.row_number()
            .over(
                partition_by=HotelRateSnapshot.hotel_id,
                order_by=effective_price.asc(),
            )
            .label("rn"),
        )
        .where(
            HotelRateSnapshot.hotel_id.in_(nearby_hotel_ids),
            HotelRateSnapshot.check_in == check_in,
            HotelRateSnapshot.check_out == check_out,
            HotelRateSnapshot.guests == guests,
            HotelRateSnapshot.currency == currency,
            HotelRateSnapshot.availability_status.notin_(["unavailable", "stale"]),
        )
        .subquery()
    )

    cheapest = db.execute(
        select(
            rates_subq.c.hotel_id,
            rates_subq.c.provider,
            rates_subq.c.amount,
            rates_subq.c.currency,
            rates_subq.c.price_semantics,
            rates_subq.c.amount_total,
            rates_subq.c.observed_at,
            rates_subq.c.snapshot_outcome,
            rates_subq.c.conditions_completeness,
        ).where(rates_subq.c.rn == 1)
    ).all()

    price_map: dict[str, HotelAreaPriceInfo] = {}
    for row in cheapest:
        price_map[row.hotel_id] = {
            "provider": row.provider,
            "amount": float(row.amount),
            "currency": row.currency,
            "price_semantics": row.price_semantics,
            "amount_total": float(row.amount_total) if row.amount_total is not None else None,
            "observed_at": row.observed_at,
            "snapshot_outcome": row.snapshot_outcome,
            "conditions_completeness": row.conditions_completeness,
        }

    # A provider-confirmed sold-out result must not fall back to an older DB
    # price for the same hotel. Fresh eligible provider rates still overlay the
    # local pool normally.
    for hotel_id in provider_unavailable_hotel_ids:
        price_map.pop(hotel_id, None)
    price_map.update(provider_price_map)

    # Check tracked offers for this user
    tracked_hotel_ids: set[str] = set()
    if user_id:
        tracked = db.scalars(
            select(HotelTrackedOffer.hotel_id).where(
                HotelTrackedOffer.user_id == user_id,
                HotelTrackedOffer.is_active.is_(True),
                HotelTrackedOffer.hotel_id.in_(nearby_hotel_ids),
            )
        ).all()
        tracked_hotel_ids = set(tracked)

    # Build results
    results: list[HotelAreaSearchResult] = []
    for hotel, distance in nearby:
        price_info = price_map.get(hotel.id)
        if price_info:
            provider = price_info["provider"]
            amount = price_info["amount"]
            curr = price_info["currency"]
            price_semantics = price_info["price_semantics"]
            amount_total = price_info["amount_total"]
            observed_at = price_info["observed_at"]
            snapshot_outcome = price_info["snapshot_outcome"]
            conditions_completeness = price_info["conditions_completeness"]
            displayed_price = (
                amount_total
                if price_semantics == "total" and amount_total is not None
                else amount
            )
            if max_price is not None and displayed_price is not None and displayed_price > max_price:
                continue
        else:
            provider, amount, curr = None, None, currency
            price_semantics = None
            amount_total = None
            observed_at = None
            snapshot_outcome = None
            conditions_completeness = None
            displayed_price = None

        results.append({
            "hotel_id": hotel.id,
            "canonical_name": hotel.canonical_name,
            "city": hotel.city,
            "country_code": hotel.country_code,
            "stars": hotel.stars,
            "distance_km": distance,
            "lowest_price": amount,
            "displayed_price": displayed_price,
            "currency": curr,
            "provider": provider,
            "price_semantics": price_semantics,
            "amount_total": amount_total,
            "observed_at": observed_at,
            "snapshot_outcome": snapshot_outcome,
            "conditions_completeness": conditions_completeness,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "has_tracking": hotel.id in tracked_hotel_ids,
        })

    # Sort
    if sort == "price":
        results.sort(
            key=lambda r: (
                r["displayed_price"] is None,
                r["displayed_price"] if r["displayed_price"] is not None else 0,
                r["distance_km"],
                r["hotel_id"],
            )
        )
    elif sort == "stars":
        results.sort(
            key=lambda r: (
                r["stars"] is None,
                -(r["stars"] or 0),
                r["distance_km"],
                r["hotel_id"],
            )
        )
    else:  # distance
        results.sort(
            key=lambda r: (
                r["distance_km"],
                r["displayed_price"] is None,
                r["displayed_price"] if r["displayed_price"] is not None else 0,
                r["hotel_id"],
            )
        )

    return results


def _provider_failure_status(exc: Exception) -> str:
    code = str(getattr(exc, "code", "")).strip().lower()
    if code in {"timeout", "rate_limited"}:
        return code
    return "failed"


def _provider_displayed_price(rate: ProviderRateRecord) -> float:
    if rate.price_semantics == "total" and rate.amount_total is not None:
        return rate.amount_total
    return rate.amount


def list_tracked_offer_snapshots(
    db: Session,
    *,
    user_id: str,
    tracked_offer_id: str,
) -> list[HotelRateSnapshot]:
    _ = get_tracked_offer_or_404(db, user_id=user_id, tracked_offer_id=tracked_offer_id)

    stmt = (
        select(HotelRateSnapshot)
        .where(HotelRateSnapshot.tracked_offer_id == tracked_offer_id)
        .order_by(desc(HotelRateSnapshot.collected_at), desc(HotelRateSnapshot.id))
    )
    return list(db.scalars(stmt))


def list_tracked_offer_history_snapshots(
    db: Session,
    *,
    user_id: str,
    tracked_offer_id: str,
    from_date: Date | None = None,
    to_date: Date | None = None,
    limit: int = 100,
) -> tuple[HotelTrackedOffer, list[HotelRateSnapshot]]:
    offer = get_tracked_offer_or_404(db, user_id=user_id, tracked_offer_id=tracked_offer_id)
    observed_or_collected = func.coalesce(HotelRateSnapshot.observed_at, HotelRateSnapshot.collected_at)
    stmt = select(HotelRateSnapshot).where(HotelRateSnapshot.tracked_offer_id == tracked_offer_id)
    if from_date is not None:
        stmt = stmt.where(observed_or_collected >= datetime.combine(from_date, time.min))
    if to_date is not None:
        stmt = stmt.where(observed_or_collected < datetime.combine(to_date + timedelta(days=1), time.min))
    stmt = stmt.order_by(asc(observed_or_collected), asc(HotelRateSnapshot.id)).limit(limit)
    return offer, list(db.scalars(stmt))


def _fetch_and_store_provider_rates(
    *,
    db: Session,
    adapter: HotelProviderAdapter,
    nearby_hotel_ids: list[str],
    check_in: Date,
    check_out: Date,
    guests: int,
    currency: str,
    provider_price_map: dict[str, HotelAreaPriceInfo],
    provider_unavailable_hotel_ids: set[str] | None = None,
    latency_sink: Callable[[ProviderLatencySample], None] | None = None,
) -> str | None:
    """Fetch fresh rates from an external provider for nearby hotels.

    Runs API calls in parallel via ThreadPoolExecutor, then stores any new
    rates as HotelRateSnapshot rows and populates provider_price_map with
    the cheapest rate per hotel from the provider.
    """
    provider_id = adapter.provider_id
    sample_lock = Lock()

    def _thread_safe_sink(sample: ProviderLatencySample) -> None:
        if latency_sink is None:
            return
        with sample_lock:
            latency_sink(sample)

    effective_latency_sink = _thread_safe_sink if latency_sink is not None else None

    # Resolve provider-level hotel IDs via HotelProviderAlias
    aliases = db.scalars(
        select(HotelProviderAlias).where(
            HotelProviderAlias.hotel_id.in_(nearby_hotel_ids),
            HotelProviderAlias.provider == provider_id,
        )
    ).all()
    aliases_by_hotel: dict[str, list[HotelProviderAlias]] = {}
    for alias in aliases:
        aliases_by_hotel.setdefault(alias.hotel_id, []).append(alias)

    # Only an unambiguous external identity may be queried. Reserve and mark
    # each request as used before scheduling any adapter I/O. Register leases
    # immediately so an exception during admission cannot strand a claim.
    budget_ledger = HotelProviderBudgetLedger(db)
    allowed_aliases: dict[
        str,
        tuple[str, HotelSweepLeaseToken | None, HotelCircuitPermit | None],
    ] = {}
    pending_area_leases: dict[str, HotelSweepLeaseToken] = {}

    def _finish_area_lease(
        hotel_id: str,
        *,
        status: str,
        error_code: str | None = None,
    ) -> bool:
        lease = pending_area_leases.get(hotel_id)
        if lease is None:
            return True
        try:
            finished = HotelSweepLeaseStore(db).finish(
                lease,
                status=status,
                now=utc_now_naive(),
                error_code=error_code,
            )
        except Exception:
            db.rollback()
            return False
        if finished:
            pending_area_leases.pop(hotel_id, None)
        return finished

    def _fail_pending_area_leases() -> None:
        for pending_hotel_id in list(pending_area_leases):
            _finish_area_lease(
                pending_hotel_id,
                status="failed",
                error_code="area_search_persistence_failed",
            )

    def _safe_add_snapshot(snapshot: HotelRateSnapshot) -> None:
        try:
            db.add(snapshot)
        except Exception:
            _fail_pending_area_leases()
            raise

    def _safe_existing_snapshots(statement: Select[tuple[HotelRateSnapshot]]) -> list[HotelRateSnapshot]:
        try:
            return list(db.scalars(statement))
        except Exception:
            _fail_pending_area_leases()
            raise

    def _safe_cheapest(rates: list[ProviderRateRecord]) -> ProviderRateRecord:
        try:
            return min(rates, key=_provider_displayed_price)
        except Exception:
            _fail_pending_area_leases()
            raise

    reservation = None
    area_lease = None
    try:
        for hotel_id in nearby_hotel_ids:
            candidates = aliases_by_hotel.get(hotel_id, [])
            if len(candidates) != 1 or not candidates[0].provider_hotel_id:
                continue
            area_lease = None
            reservation = None
            circuit_permit: HotelCircuitPermit | None = None
            if is_hotel_provider_external(provider_id):
                admission = HotelProviderCircuitStore(db).admit(
                    provider_id,
                    "area_search",
                    now=utc_now_naive(),
                )
                if not admission.allowed or admission.permit is None:
                    continue
                circuit_permit = admission.permit
                reservation = budget_ledger.reserve(policy_from_env(provider_id, "area_search"))
                if not reservation.allowed:
                    continue
                query_fingerprint = stay_query_fingerprint(
                    provider=provider_id,
                    operation="area_search",
                    canonical_hotel_id=hotel_id,
                    provider_hotel_id=candidates[0].provider_hotel_id,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    currency=currency,
                )
                area_lease = HotelSweepLeaseStore(db).acquire(
                    query_fingerprint,
                    now=utc_now_naive(),
                    ttl_seconds=60,
                )
                if area_lease is None:
                    budget_ledger.release(reservation)
                    continue
                pending_area_leases[hotel_id] = area_lease
                try:
                    consumed = budget_ledger.consume(reservation)
                except Exception:
                    # A ledger exception still means no adapter call occurred;
                    # return the admission before propagating the failure.
                    budget_ledger.release(reservation)
                    _finish_area_lease(
                        hotel_id,
                        status="failed",
                        error_code="budget_consume_failed",
                    )
                    raise
                if not consumed:
                    # The adapter was never scheduled; release the reservation
                    # before closing the failed lease.
                    budget_ledger.release(reservation)
                    _finish_area_lease(
                        hotel_id,
                        status="failed",
                        error_code="budget_consume_failed",
                    )
                    continue
            allowed_aliases[hotel_id] = (
                candidates[0].provider_hotel_id,
                area_lease,
                circuit_permit,
            )
    except Exception:
        if reservation is not None and reservation.allowed:
            budget_ledger.release(reservation)
        _fail_pending_area_leases()
        raise

    if not allowed_aliases:
        return None

    def _fetch_one(
        hotel_id: str,
        provider_hotel_id: str,
    ) -> tuple[str, list[ProviderRateRecord] | Exception]:
        try:
            measurement = measure_provider_call(
                lambda: adapter.fetch_hotel_rates(
                    hotel_id=provider_hotel_id,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    currency=currency,
                ),
                provider=adapter.provider_id,
                operation="area_search",
                classify_result=lambda value: ("empty" if not value else "success", None),
                classify_exception=lambda _: ("failed", "provider_fetch_failed"),
                on_sample=effective_latency_sink,
                propagate_exception=True,
            )
            assert measurement is not None
            rates = measurement.value or []
            return hotel_id, rates
        except Exception as exc:
            # Preserve failure-vs-empty semantics. An exception must close the
            # lease as failed and must not become a false empty observation.
            return hotel_id, exc

    # Fetch in parallel (max 5 concurrent API calls)
    fetched: list[tuple[str, list[ProviderRateRecord] | Exception]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # ContextVars are task-local, not thread-local. Copy the request
        # context per submitted call so provider headers/logs retain the
        # correlation and client intent in parallel area-search fetches.
        futures = {
            executor.submit(
                copy_context().run,
                _fetch_one,
                h_id,
                allowed_aliases[h_id][0],
            ): h_id
            for h_id in nearby_hotel_ids
            if h_id in allowed_aliases
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                fetched.append(future.result())
            except Exception:
                _fail_pending_area_leases()
                raise

    # Store new rates and build provider price map. The lease is finished only
    # after pending snapshots have been added, so its token check and the
    # snapshot write are committed as one transaction.
    failure_status: str | None = None
    for h_id, fetched_result in fetched:
        area_lease = allowed_aliases[h_id][1]
        circuit_permit = allowed_aliases[h_id][2]
        if isinstance(fetched_result, Exception):
            failure_status = failure_status or _provider_failure_status(fetched_result)
            if circuit_permit is not None:
                _record_hotel_circuit_outcome(db, circuit_permit, "failed")
            if area_lease is not None:
                _finish_area_lease(
                    h_id,
                    status="failed",
                    error_code="provider_fetch_failed",
                )
            continue

        rates = fetched_result
        if not rates:
            if circuit_permit is not None:
                _record_hotel_circuit_outcome(db, circuit_permit, "empty")
            if area_lease is not None:
                _finish_area_lease(h_id, status="done")
            continue
        if circuit_permit is not None:
            _record_hotel_circuit_outcome(db, circuit_permit, "success")

        # Check existing rates to avoid duplicates
        existing = _safe_existing_snapshots(
            select(HotelRateSnapshot).where(
                HotelRateSnapshot.hotel_id == h_id,
                HotelRateSnapshot.provider == provider_id,
                HotelRateSnapshot.check_in == check_in,
                HotelRateSnapshot.check_out == check_out,
                HotelRateSnapshot.guests == guests,
                HotelRateSnapshot.currency == currency,
            )
        )
        existing_keys = {
            (r.check_in, r.check_out, r.guests, r.currency, float(r.amount), r.availability_status)
            for r in existing
        }

        for rate in rates:
            key = (
                rate.check_in,
                rate.check_out,
                rate.guests,
                rate.currency,
                rate.amount,
                rate.availability_status,
            )
            if key not in existing_keys:
                _safe_add_snapshot(
                    HotelRateSnapshot(
                        hotel_id=h_id,
                        provider=provider_id,
                        check_in=rate.check_in,
                        check_out=rate.check_out,
                        guests=rate.guests,
                        room_label=rate.room_label,
                        meal_plan=rate.meal_plan,
                        cancellation_policy=rate.cancellation_policy,
                        currency=rate.currency,
                        amount=rate.amount,
                        amount_total=rate.amount_total if rate.price_semantics == "total" else None,
                        availability_status=rate.availability_status,
                        observed_at=utc_now_naive(),
                        snapshot_outcome="success",
                        price_semantics=rate.price_semantics,
                        conditions_completeness=rate.conditions_completeness,
                        deep_link=sanitize_hotel_deep_link(rate.deep_link, provider=provider_id),
                    )
                )
                existing_keys.add(key)

        # The conditional update in finish() rejects an expired/taken lease;
        # its commit includes the snapshots added above.
        if area_lease is not None and not _finish_area_lease(h_id, status="done"):
            # The conditional update says this worker no longer owns the
            # lease; never write a late snapshot or retry with its token.
            pending_area_leases.pop(h_id, None)
            db.rollback()
            continue

        # Availability observations remain persisted, but sold-out rates are
        # never advertised as the cheapest eligible price. If the provider
        # returned only sold-out rates, prevent a stale local price fallback.
        eligible_rates = [rate for rate in rates if rate.availability_status not in {"unavailable", "stale"}]
        if not eligible_rates and provider_unavailable_hotel_ids is not None:
            provider_unavailable_hotel_ids.add(h_id)
        if eligible_rates:
            cheapest = _safe_cheapest(eligible_rates)
            provider_price_map[h_id] = {
                "provider": provider_id,
                "amount": cheapest.amount,
                "currency": cheapest.currency,
                "price_semantics": cheapest.price_semantics,
                "amount_total": cheapest.amount_total if cheapest.price_semantics == "total" else None,
                "observed_at": utc_now_naive(),
                "snapshot_outcome": "success",
                "conditions_completeness": cheapest.conditions_completeness,
            }

    # Any lease still present here was not assigned a terminal outcome (for
    # example, an unexpected per-rate exception). Close it before returning.
    _fail_pending_area_leases()
    try:
        db.flush()
    except Exception:
        _fail_pending_area_leases()
        raise
    return failure_status
