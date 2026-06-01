from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.hotels.ingestion import HotelIngestionService
from app.hotels.normalization import HotelNormalizationService
from app.hotels.parity import HotelParityService, ParitySignal
from app.infrastructure.db.models import (
    HotelAlertRule,
    HotelCompSet,
    HotelCompSetMember,
    HotelProperty,
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
