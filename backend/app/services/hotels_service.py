from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.hotels.geo import HotelGeoService, HotelNearbySuggestion, haversine_km
from app.hotels.normalization import HotelNormalizationService
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
    HotelTrackedOffer,
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
    hotel_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[HotelAlertEvent]:
    stmt = select(HotelAlertEvent).join(HotelAlertRule, HotelAlertEvent.rule_id == HotelAlertRule.id).where(HotelAlertRule.user_id == user_id)
    if hotel_id is not None:
        stmt = stmt.where(HotelAlertEvent.hotel_id == hotel_id)
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

    # Get cheapest rate per hotel for the given criteria
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

    # Check tracked offers for this user
    tracked_hotel_ids: set[str] = set()
    if user_id:
        tracked = db.scalars(
            select(HotelTrackedOffer.hotel_id).where(
                HotelTrackedOffer.user_id == user_id,
                HotelTrackedOffer.is_active == True,
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
