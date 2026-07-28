from collections.abc import Mapping, Sequence
from datetime import date as Date, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.domain.schemas import (
    CommunityPriceAggregateOut,
    CommunityPriceResponseOut,
    CommunityPricingOut,
)
from app.domain.vocabulary import WATCH_STATUS_PURCHASED
from app.infrastructure.db.models import CommunityPriceReport, FlightWatch

COMMUNITY_PRICE_MINIMUM_SAMPLE_SIZE = 3
COMMUNITY_PRICE_WINDOW_DAYS = 365

CommunityRouteKey = tuple[str, str]
CommunityAggregateRow = tuple[int, float | None, float | None]


def community_trigger_reason(
    watch: FlightWatch,
    *,
    today: Date | None = None,
) -> str | None:
    current_date = today or Date.today()
    if watch.status == WATCH_STATUS_PURCHASED:
        return "purchased"
    if watch.travel_date_local < current_date:
        return "expired"
    return None


def build_community_pricing_by_watch(
    db: Session,
    watches: Sequence[FlightWatch],
    *,
    current_user_id: str,
    today: Date | None = None,
) -> Mapping[str, CommunityPricingOut]:
    if not watches:
        return {}

    current_date = today or Date.today()
    watch_ids = [watch.id for watch in watches]
    reports = list(
        db.scalars(
            select(CommunityPriceReport).where(
                CommunityPriceReport.user_id == current_user_id,
                CommunityPriceReport.watch_id.in_(watch_ids),
            )
        )
    )
    report_by_watch_id = {report.watch_id: report for report in reports}
    route_keys = {(watch.origin_iata, watch.destination_iata) for watch in watches}
    aggregate_by_route = _aggregate_by_route(
        db,
        route_keys,
        today=current_date,
    )

    result: dict[str, CommunityPricingOut] = {}
    for watch in watches:
        route_key = (watch.origin_iata, watch.destination_iata)
        sample_size, min_price, max_price = aggregate_by_route.get(route_key, (0, None, None))
        is_public = sample_size >= COMMUNITY_PRICE_MINIMUM_SAMPLE_SIZE
        report = report_by_watch_id.get(watch.id)
        trigger_reason = community_trigger_reason(watch, today=current_date)
        result[watch.id] = CommunityPricingOut(
            eligible=trigger_reason is not None,
            trigger_reason=trigger_reason,
            response=(
                None
                if report is None
                else CommunityPriceResponseOut(
                    flew=report.flew,
                    price_per_traveler=(
                        float(report.price_per_traveler)
                        if report.price_per_traveler is not None
                        else None
                    ),
                    currency="EUR",
                )
            ),
            aggregate=CommunityPriceAggregateOut(
                sample_size=sample_size,
                minimum_sample_size=COMMUNITY_PRICE_MINIMUM_SAMPLE_SIZE,
                is_public=is_public,
                min_price=min_price if is_public else None,
                max_price=max_price if is_public else None,
                currency="EUR",
            ),
        )
    return result


def community_pricing_for_watch(
    db: Session,
    watch: FlightWatch,
    *,
    current_user_id: str,
    today: Date | None = None,
) -> CommunityPricingOut:
    return build_community_pricing_by_watch(
        db,
        [watch],
        current_user_id=current_user_id,
        today=today,
    )[watch.id]


def _aggregate_by_route(
    db: Session,
    route_keys: set[CommunityRouteKey],
    *,
    today: Date,
) -> Mapping[CommunityRouteKey, CommunityAggregateRow]:
    if not route_keys:
        return {}

    origins = {origin for origin, _ in route_keys}
    destinations = {destination for _, destination in route_keys}
    start_date = today - timedelta(days=COMMUNITY_PRICE_WINDOW_DAYS)
    rows = db.execute(
        select(
            FlightWatch.origin_iata,
            FlightWatch.destination_iata,
            func.count(distinct(CommunityPriceReport.user_id)),
            func.min(CommunityPriceReport.price_per_traveler),
            func.max(CommunityPriceReport.price_per_traveler),
        )
        .join(FlightWatch, FlightWatch.id == CommunityPriceReport.watch_id)
        .where(
            CommunityPriceReport.flew.is_(True),
            CommunityPriceReport.price_per_traveler.is_not(None),
            FlightWatch.origin_iata.in_(origins),
            FlightWatch.destination_iata.in_(destinations),
            FlightWatch.travel_date_local >= start_date,
            FlightWatch.travel_date_local <= today,
        )
        .group_by(FlightWatch.origin_iata, FlightWatch.destination_iata)
    ).all()

    aggregates: dict[CommunityRouteKey, CommunityAggregateRow] = {}
    for origin_iata, destination_iata, sample_size, min_price, max_price in rows:
        route_key = (origin_iata, destination_iata)
        if route_key not in route_keys:
            continue
        aggregates[route_key] = (
            int(sample_size),
            float(min_price) if min_price is not None else None,
            float(max_price) if max_price is not None else None,
        )
    return aggregates
