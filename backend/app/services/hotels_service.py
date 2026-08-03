from __future__ import annotations

import concurrent.futures
import logging

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.i18n import t
from app.hotels.contracts import ProviderRateRecord
from app.hotels.geo import HotelGeoService, HotelNearbySuggestion, haversine_km
from app.hotels.normalization import HotelNormalizationService
from app.hotels.ingestion import HotelIngestionService
from app.hotels.parity import HotelParityService, ParitySignal
from app.infrastructure.db.models import (
    HotelAlertEvent,
    HotelAlertRule,
    HotelCompSet,
    HotelCompSetMember,
    HotelProperty,
    HotelProviderAlias,
    HotelProviderRun,
    HotelRateSnapshot,
    HotelTrackedOffer,
    HotelWatchlistItem,
)

logger = logging.getLogger(__name__)


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
    stmt = select(HotelRateSnapshot).where(HotelRateSnapshot.hotel_id == hotel_id)
    if check_in is not None:
        stmt = stmt.where(HotelRateSnapshot.check_in >= check_in)
    if check_out is not None:
        stmt = stmt.where(HotelRateSnapshot.check_out <= check_out)
    stmt = stmt.order_by(desc(HotelRateSnapshot.collected_at), desc(HotelRateSnapshot.id))
    return list(db.scalars(stmt))


def ingest_hotels_mock(db: Session):
    return HotelIngestionService(db).ingest()


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
) -> HotelAlertRule:
    _ = get_hotel_or_404(db, hotel_id)
    rule = HotelAlertRule(
        user_id=user_id,
        hotel_id=hotel_id,
        tracked_offer_id=tracked_offer_id,
        rule_type=rule_type,
        threshold_amount=threshold_amount,
        threshold_percent=threshold_percent,
        compare_against=compare_against,
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
        if field not in {"rule_type", "threshold_amount", "threshold_percent", "compare_against", "is_active"}:
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


def run_hotel_sweep(db: Session, *, provider: str = "mock") -> HotelProviderRun:
    provider_run = HotelProviderRun(provider=provider, status="running")
    db.add(provider_run)
    db.flush()

    adapter = None
    try:
        if provider == "mock":
            result = ingest_hotels_mock(db)
        elif provider == "makcorps":
            from app.hotels.ingestion import HotelIngestionService, resolve_hotel_provider

            adapter = resolve_hotel_provider()
            result = HotelIngestionService(db, provider=adapter).ingest()
        else:
            raise ValueError(f"Unsupported sweep provider: {provider}")

        provider_run.items_processed = result.hotels_processed
        provider_run.status = "completed"
        db.flush()

        evaluate_hotel_alerts(db, provider_run_id=provider_run.id)
        sweep_tracked_offers(db, provider_run_id=provider_run.id, provider_adapter=adapter)
    except Exception as exc:
        provider_run.status = "failed"
        provider_run.error_message = str(exc)[:500]
        db.flush()

    provider_run.finished_at = utc_now_naive()
    db.commit()
    db.refresh(provider_run)
    return provider_run


def sweep_tracked_offers(
    db: Session,
    *,
    provider_run_id: str,
    provider_adapter: object | None = None,
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

    Returns a dict with counts: {"offers_scanned": N, "snapshots_created": M}.
    """
    active_offers = list(
        db.scalars(
            select(HotelTrackedOffer).where(
                HotelTrackedOffer.is_active.is_(True),
                HotelTrackedOffer.check_in.is_not(None),
                HotelTrackedOffer.check_out.is_not(None),
            )
        )
    )

    offers_scanned = 0
    snapshots_created = 0

    for offer in active_offers:
        offers_scanned += 1

        if offer.check_in is None or offer.check_out is None:
            continue

        # Try fetching targeted rates from the provider adapter first
        provider_rates: list[ProviderRateRecord] = []
        if provider_adapter is not None and hasattr(provider_adapter, "fetch_hotel_rates"):
            try:
                provider_rates = provider_adapter.fetch_hotel_rates(
                    hotel_id=offer.hotel_id,
                    check_in=offer.check_in,
                    check_out=offer.check_out,
                    guests=offer.guests or 2,
                    currency=offer.currency or "EUR",
                )
            except Exception:
                provider_rates = []

        # Determine the rate to use: provider rates first, then fallback to unlinked snapshots
        if provider_rates:
            # Use the cheapest rate from the provider
            best = min(provider_rates, key=lambda r: r.amount)
            rate_amount = best.amount
            rate_provider = provider_adapter.provider_id if hasattr(provider_adapter, "provider_id") else "makcorps"
            rate_room = best.room_label or offer.room_label
            rate_meal = best.meal_plan or offer.meal_plan
            rate_cancellation = best.cancellation_policy or offer.cancellation_policy
            rate_check_in = best.check_in
            rate_check_out = best.check_out
            rate_currency = best.currency
            rate_guests = best.guests
            rate_availability = "available"
            rate_deep_link = None
        else:
            # Fallback: find cheapest unlinked snapshot from general pool
            cheapest = db.scalars(
                select(HotelRateSnapshot)
                .where(
                    HotelRateSnapshot.hotel_id == offer.hotel_id,
                    HotelRateSnapshot.check_in == offer.check_in,
                    HotelRateSnapshot.check_out == offer.check_out,
                    HotelRateSnapshot.guests == offer.guests,
                    HotelRateSnapshot.currency == offer.currency,
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
            rate_deep_link = cheapest.deep_link

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

        # Update current_price on the tracked offer
        new_price = rate_amount
        offer.current_price = new_price
        db.add(offer)

        # Create alert event if price changed from previous
        hotel = db.get(HotelProperty, offer.hotel_id)
        hotel_name = hotel.canonical_name if hotel else offer.hotel_id

        if previous_price is not None and previous_price != new_price:
            delta = new_price - previous_price
            pct = round((delta / previous_price) * 100, 1) if previous_price > 0 else 0.0
            direction = t("es", "hotels.direction.rose") if delta > 0 else t("es", "hotels.direction.dropped")
            event_type = "price_above" if delta > 0 else "price_below"

            db.add(
                HotelAlertEvent(
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
                )
            )

    if snapshots_created > 0:
        db.flush()

    return {"offers_scanned": offers_scanned, "snapshots_created": snapshots_created}


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
            if tracked_offer is None:
                continue
            snapshots = list_tracked_offer_snapshots(
                db, user_id=tracked_offer.user_id, tracked_offer_id=tracked_offer.id
            )
            if not snapshots:
                continue
            _evaluate_tracked_alert_rule(
                db, rule, snapshots, hotel_name, provider_run_id, events
            )
            continue

        # Legacy: evaluate against all rates for the hotel
        rates = list_hotel_rates(db, hotel_id=rule.hotel_id, check_in=None, check_out=None)
        if not rates:
            continue

        if rule.rule_type == "price_below":
            amounts_f = [float(r.amount) for r in rates]
            avg = sum(amounts_f) / len(amounts_f) if rule.threshold_percent is not None and len(amounts_f) > 0 else None
            for rate in rates:
                triggered = False
                trigger_value = None
                rate_f = float(rate.amount)
                if rule.threshold_amount is not None and rate_f < float(rule.threshold_amount):
                    triggered = True
                    trigger_value = rate_f
                if avg is not None and avg > 0 and ((avg - rate_f) / avg * 100) >= float(rule.threshold_percent):
                    triggered = True
                    trigger_value = rate_f
                if triggered:
                    events.append(
                        HotelAlertEvent(
                            rule_id=rule.id,
                            hotel_id=rule.hotel_id,
                            provider_run_id=provider_run_id,
                            event_type="price_below",
                            message=f"{hotel_name}: {rate.provider} @ {rate.currency} {rate.amount:.2f}",
                            trigger_value=trigger_value,
                        )
                    )
                    break

        elif rule.rule_type == "price_above":
            amounts_f = [float(r.amount) for r in rates]
            avg = sum(amounts_f) / len(amounts_f) if rule.threshold_percent is not None and len(amounts_f) > 0 else None
            for rate in rates:
                triggered = False
                trigger_value = None
                rate_f = float(rate.amount)
                if rule.threshold_amount is not None and rate_f > float(rule.threshold_amount):
                    triggered = True
                    trigger_value = rate_f
                if avg is not None and avg > 0 and ((rate_f - avg) / avg * 100) >= float(rule.threshold_percent):
                    triggered = True
                    trigger_value = rate_f
                if triggered:
                    events.append(
                        HotelAlertEvent(
                            rule_id=rule.id,
                            hotel_id=rule.hotel_id,
                            provider_run_id=provider_run_id,
                            event_type="price_above",
                            message=f"{hotel_name}: {rate.provider} @ {rate.currency} {rate.amount:.2f}",
                            trigger_value=trigger_value,
                        )
                    )
                    break

        elif rule.rule_type == "parity_break":
            signals = HotelParityService.compute_parity(rates)
            for signal in signals:
                if signal.is_parity_broken and signal.spread_percent is not None and (rule.threshold_percent is None or signal.spread_percent >= rule.threshold_percent):
                    events.append(
                        HotelAlertEvent(
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
            _evaluate_legacy_percentage_rule(db, rule, rates, hotel_name, provider_run_id, events, direction="drop")
        elif rule.rule_type == "percentage_increase":
            _evaluate_legacy_percentage_rule(db, rule, rates, hotel_name, provider_run_id, events, direction="increase")

    for event in events:
        db.add(event)

    if events:
        db.flush()

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
    latest_amount = float(latest.amount)
    previous: HotelRateSnapshot | None = snapshots[1] if len(snapshots) > 1 else None

    # Determine the comparison baseline based on compare_against
    compare_baseline: float | None = None
    if rule.compare_against == "initial_price":
        tracked_offer = db.get(HotelTrackedOffer, rule.tracked_offer_id) if rule.tracked_offer_id else None
        if tracked_offer is not None and tracked_offer.initial_price is not None:
            compare_baseline = float(tracked_offer.initial_price)
    elif previous is not None:
        compare_baseline = float(previous.amount)

    if rule.rule_type == "price_below":
        if rule.threshold_amount is not None and latest_amount < float(rule.threshold_amount):
            events.append(
                HotelAlertEvent(
                    rule_id=rule.id,
                    hotel_id=rule.hotel_id,
                    provider_run_id=provider_run_id,
                    event_type="price_below",
                    message=t("es", "hotels.message.price_dropped_to", hotel=hotel_name, currency=latest.currency, amount=f"{latest_amount:.2f}"),
                    trigger_value=latest_amount,
                )
            )

    elif rule.rule_type == "price_above":
        if rule.threshold_amount is not None and latest_amount > float(rule.threshold_amount):
            events.append(
                HotelAlertEvent(
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
                    rule_id=rule.id,
                    hotel_id=rule.hotel_id,
                    provider_run_id=provider_run_id,
                    event_type="provider_changed",
                    message=t("es", "hotels.message.provider_changed", hotel=hotel_name, previous_provider=previous.provider or "?", current_provider=latest.provider or "?"),
                    trigger_value=latest_amount,
                )
            )

    elif rule.rule_type == "availability_returned" and previous is not None and previous.availability_status == "unavailable" and latest.availability_status == "available":
        events.append(
            HotelAlertEvent(
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
    # Include events from both alert rules and sweep-generated (rule_id is None)
    rule_hotel_ids_query = select(HotelAlertRule.hotel_id).where(HotelAlertRule.user_id == user_id)
    if hotel_id is not None:
        rule_hotel_ids_query = rule_hotel_ids_query.where(HotelAlertRule.hotel_id == hotel_id)
    allowed_hotel_ids = set(db.scalars(rule_hotel_ids_query).all())

    # Also include tracked offer hotel IDs for sweep-generated events
    tracked_hotel_ids_query = select(HotelTrackedOffer.hotel_id).where(HotelTrackedOffer.user_id == user_id)
    if hotel_id is not None:
        tracked_hotel_ids_query = tracked_hotel_ids_query.where(HotelTrackedOffer.hotel_id == hotel_id)
    allowed_hotel_ids.update(db.scalars(tracked_hotel_ids_query).all())

    if not allowed_hotel_ids:
        return []

    stmt = select(HotelAlertEvent).where(HotelAlertEvent.hotel_id.in_(allowed_hotel_ids))
    stmt = stmt.order_by(desc(HotelAlertEvent.created_at), desc(HotelAlertEvent.id)).offset(offset).limit(limit)
    return list(db.scalars(stmt))


# ── HotelTrackedOffer ──────────────────────────────────────────────


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
    check_in: object | None = None,
    check_out: object | None = None,
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

    # Create initial snapshot with the tracked offer reference
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

    for field, value in update_data.items():
        if field in allowed:
            setattr(offer, field, value)

    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def delete_tracked_offer(db: Session, *, user_id: str, tracked_offer_id: str) -> None:
    offer = get_tracked_offer_or_404(db, user_id=user_id, tracked_offer_id=tracked_offer_id)
    db.delete(offer)
    db.commit()


def area_resolve(
    db: Session,
    *,
    q: str,
) -> dict[str, object]:
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
            return geocode_result

        raise ValueError("area_not_found")

    # Compute centroid
    lats = [float(h.latitude) for h in hotels]
    lngs = [float(h.longitude) for h in hotels]
    countries = {h.country_code for h in hotels}

    avg_lat = sum(lats) / len(lats)
    avg_lng = sum(lngs) / len(lngs)

    # Determine confidence based on city convergence
    if len(hotels) >= 3:
        confidence = "high"
    elif len(hotels) == 1:
        confidence = "low"
    else:
        confidence = "medium"

    # Build area label from the most common city
    city_counts: dict[str, int] = {}
    for h in hotels:
        city_counts[h.city] = city_counts.get(h.city, 0) + 1
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
    check_in: object,
    check_out: object,
    guests: int,
    currency: str,
    min_stars: int | None = None,
    max_price: float | None = None,
    sort: str = "price",
    user_id: str | None = None,
    use_provider: bool = False,
) -> list[dict[str, object]]:
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
    provider_price_map: dict[str, tuple[str, float, str]] = {}
    if use_provider:
        try:
            from app.hotels.ingestion import resolve_hotel_provider

            adapter = resolve_hotel_provider()
            if hasattr(adapter, "fetch_hotel_rates") and hasattr(adapter, "provider_id"):
                _fetch_and_store_provider_rates(
                    db=db,
                    adapter=adapter,
                    nearby_hotel_ids=nearby_hotel_ids,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    currency=currency,
                    provider_price_map=provider_price_map,
                )
        except Exception as exc:
            logger.warning("area_search provider fetch skipped: %s", exc)

    # Get cheapest rate per hotel for the given criteria (DB fallback)
    rates_subq = (
        select(
            HotelRateSnapshot.hotel_id,
            HotelRateSnapshot.provider,
            HotelRateSnapshot.amount,
            HotelRateSnapshot.currency,
            func.row_number()
            .over(
                partition_by=HotelRateSnapshot.hotel_id,
                order_by=HotelRateSnapshot.amount.asc(),
            )
            .label("rn"),
        )
        .where(
            HotelRateSnapshot.hotel_id.in_(nearby_hotel_ids),
            HotelRateSnapshot.check_in == check_in,
            HotelRateSnapshot.check_out == check_out,
            HotelRateSnapshot.guests == guests,
            HotelRateSnapshot.currency == currency,
        )
        .subquery()
    )

    cheapest = db.execute(
        select(
            rates_subq.c.hotel_id,
            rates_subq.c.provider,
            rates_subq.c.amount,
            rates_subq.c.currency,
        ).where(rates_subq.c.rn == 1)
    ).all()

    price_map: dict[str, tuple[str, float, str]] = {}
    for row in cheapest:
        price_map[row.hotel_id] = (row.provider, float(row.amount), row.currency)

    # Overlay provider rates (fresh external data takes priority over stale DB rates)
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
    results: list[dict[str, object]] = []
    for hotel, distance in nearby:
        price_info = price_map.get(hotel.id)
        if price_info:
            provider, amount, curr = price_info
            if max_price is not None and amount > max_price:
                continue
        else:
            provider, amount, curr = None, None, currency

        results.append({
            "hotel_id": hotel.id,
            "canonical_name": hotel.canonical_name,
            "city": hotel.city,
            "country_code": hotel.country_code,
            "stars": hotel.stars,
            "distance_km": distance,
            "lowest_price": amount,
            "currency": curr,
            "provider": provider,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "has_tracking": hotel.id in tracked_hotel_ids,
        })

    # Sort
    if sort == "price":
        results.sort(key=lambda r: (r["lowest_price"] if r["lowest_price"] is not None else float("inf"), r["distance_km"]))
    elif sort == "stars":
        results.sort(key=lambda r: (-(r["stars"] or 0), r["distance_km"]))
    else:  # distance
        results.sort(key=lambda r: r["distance_km"])

    return results


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


def _fetch_and_store_provider_rates(
    *,
    db: Session,
    adapter: object,
    nearby_hotel_ids: list[str],
    check_in: object,
    check_out: object,
    guests: int,
    currency: str,
    provider_price_map: dict[str, tuple[str, float, str]],
) -> None:
    """Fetch fresh rates from an external provider for nearby hotels.

    Runs API calls in parallel via ThreadPoolExecutor, then stores any new
    rates as HotelRateSnapshot rows and populates provider_price_map with
    the cheapest rate per hotel from the provider.
    """
    provider_id: str = getattr(adapter, "provider_id", "makcorps")

    # Resolve provider-level hotel IDs via HotelProviderAlias
    aliases = db.scalars(
        select(HotelProviderAlias).where(
            HotelProviderAlias.hotel_id.in_(nearby_hotel_ids),
            HotelProviderAlias.provider == provider_id,
        )
    ).all()
    alias_map: dict[str, str] = {a.hotel_id: a.provider_hotel_id for a in aliases}

    if not alias_map:
        return

    def _fetch_one(hotel_id: str, provider_hotel_id: str) -> tuple[str, list[ProviderRateRecord]]:
        try:
            rates = adapter.fetch_hotel_rates(
                hotel_id=provider_hotel_id,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                currency=currency,
            )
            return hotel_id, rates
        except Exception:
            return hotel_id, []

    # Fetch in parallel (max 5 concurrent API calls)
    fetched: list[tuple[str, list[ProviderRateRecord]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_fetch_one, h_id, alias_map[h_id]): h_id
            for h_id in nearby_hotel_ids
            if h_id in alias_map
        }
        for future in concurrent.futures.as_completed(futures):
            fetched.append(future.result())

    # Store new rates and build provider price map
    new_snapshots: list[HotelRateSnapshot] = []
    for h_id, rates in fetched:
        if not rates:
            continue

        # Check existing rates to avoid duplicates
        existing = db.scalars(
            select(HotelRateSnapshot).where(
                HotelRateSnapshot.hotel_id == h_id,
                HotelRateSnapshot.provider == provider_id,
                HotelRateSnapshot.check_in == check_in,
                HotelRateSnapshot.check_out == check_out,
                HotelRateSnapshot.guests == guests,
                HotelRateSnapshot.currency == currency,
            )
        ).all()
        existing_keys = {(r.check_in, r.check_out, r.guests, r.currency, float(r.amount)) for r in existing}

        for rate in rates:
            key = (rate.check_in, rate.check_out, rate.guests, rate.currency, rate.amount)
            if key not in existing_keys:
                new_snapshots.append(
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
                        availability_status="available",
                    )
                )
                existing_keys.add(key)

        # Record cheapest provider rate for this hotel
        cheapest = min(rates, key=lambda r: r.amount)
        provider_price_map[h_id] = (provider_id, cheapest.amount, cheapest.currency)

    if new_snapshots:
        db.add_all(new_snapshots)
        db.flush()
