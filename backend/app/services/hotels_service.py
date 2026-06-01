from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.hotels.ingestion import HotelIngestionService
from app.hotels.normalization import HotelNormalizationService
from app.hotels.parity import HotelParityService, ParitySignal
from app.infrastructure.db.models import (
    HotelAlertEvent,
    HotelAlertRule,
    HotelCompSet,
    HotelCompSetMember,
    HotelProperty,
    HotelProviderRun,
    HotelRateSnapshot,
    HotelWatchlistItem,
)


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
        stmt = stmt.where(HotelProperty.city.ilike(f"%{normalized_city}%"))
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


def list_comp_set_members(db: Session, comp_set_id: str) -> list[HotelCompSetMember]:
    return list(db.scalars(select(HotelCompSetMember).where(HotelCompSetMember.comp_set_id == comp_set_id).order_by(HotelCompSetMember.id.asc())))


def add_comp_set_member(db: Session, *, user_id: str, comp_set_id: str, hotel_id: str) -> HotelCompSetMember:
    _ = get_comp_set_or_404(db, user_id=user_id, comp_set_id=comp_set_id)
    _ = get_hotel_or_404(db, hotel_id)
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
) -> HotelAlertRule:
    _ = get_hotel_or_404(db, hotel_id)
    rule = HotelAlertRule(
        user_id=user_id,
        hotel_id=hotel_id,
        rule_type=rule_type,
        threshold_amount=threshold_amount,
        threshold_percent=threshold_percent,
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
        if field not in {"rule_type", "threshold_amount", "threshold_percent", "is_active"}:
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
    except Exception as exc:
        provider_run.status = "failed"
        provider_run.error_message = str(exc)[:500]
        db.flush()

    provider_run.finished_at = utc_now_naive()
    db.commit()
    db.refresh(provider_run)
    return provider_run


def evaluate_hotel_alerts(db: Session, *, provider_run_id: str) -> list[HotelAlertEvent]:
    rules = list(db.scalars(select(HotelAlertRule).where(HotelAlertRule.is_active == True)))
    events: list[HotelAlertEvent] = []

    for rule in rules:
        rates = list_hotel_rates(db, hotel_id=rule.hotel_id, check_in=None, check_out=None)
        if not rates:
            continue

        hotel = db.get(HotelProperty, rule.hotel_id)
        hotel_name = hotel.canonical_name if hotel else rule.hotel_id

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
                if signal.is_parity_broken and signal.spread_percent is not None:
                    if rule.threshold_percent is None or signal.spread_percent >= rule.threshold_percent:
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

    for event in events:
        db.add(event)

    if events:
        db.flush()

    return events


def list_hotel_alert_events(
    db: Session,
    *,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[HotelAlertEvent]:
    stmt = (
        select(HotelAlertEvent)
        .join(HotelAlertRule, HotelAlertEvent.rule_id == HotelAlertRule.id)
        .where(HotelAlertRule.user_id == user_id)
        .order_by(desc(HotelAlertEvent.created_at), desc(HotelAlertEvent.id))
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(stmt))
