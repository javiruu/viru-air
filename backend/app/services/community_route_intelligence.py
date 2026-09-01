from collections.abc import Mapping, Sequence
from datetime import date as Date, timedelta
from math import ceil

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.domain.schemas import (
    CommunityPopularRouteOut,
    CommunityRelatedRouteOut,
    CommunityRouteIn,
    CommunityRouteInsightOut,
)
from app.domain.vocabulary import WATCH_STATUS_DELETED
from app.infrastructure.airports_catalog import get_airport
from app.infrastructure.db.models import FlightWatch, QuickSearchPopularityDaily
from app.services.community_pricing import (
    COMMUNITY_PRICE_MINIMUM_SAMPLE_SIZE,
    aggregate_community_prices_by_route,
)

POPULARITY_WINDOW_DAYS = 7
RELATED_ROUTE_MINIMUM_USERS = 3
TRENDING_SHARE = 0.2

RouteKey = tuple[str, str]


def list_popular_routes(
    db: Session,
    *,
    limit: int = 10,
    today: Date | None = None,
) -> list[CommunityPopularRouteOut]:
    rows = _popularity_rows(db, today=today)
    trending_count = ceil(len(rows) * TRENDING_SHARE)
    return [
        CommunityPopularRouteOut(
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            searches_count=int(searches_count),
            is_trending=index < trending_count,
        )
        for index, (origin_iata, destination_iata, searches_count) in enumerate(
            rows[:limit]
        )
    ]


def build_route_insights(
    db: Session,
    routes: Sequence[CommunityRouteIn],
    *,
    today: Date | None = None,
) -> list[CommunityRouteInsightOut]:
    current_date = today or Date.today()
    route_keys = {(route.origin_iata, route.destination_iata) for route in routes}
    prices = aggregate_community_prices_by_route(
        db,
        route_keys,
        today=current_date,
    )
    popularity = _popularity_by_route(db, today=current_date)
    ranked_keys = list(popularity)
    trending_keys = set(ranked_keys[: ceil(len(ranked_keys) * TRENDING_SHARE)])

    result: list[CommunityRouteInsightOut] = []
    for route in routes:
        route_key = (route.origin_iata, route.destination_iata)
        sample_size, min_price, max_price = prices.get(route_key, (0, None, None))
        is_public = sample_size >= COMMUNITY_PRICE_MINIMUM_SAMPLE_SIZE
        result.append(
            CommunityRouteInsightOut(
                origin_iata=route.origin_iata,
                destination_iata=route.destination_iata,
                searches_count=popularity.get(route_key, 0),
                is_trending=route_key in trending_keys,
                sample_size=sample_size if is_public else 0,
                min_price=min_price if is_public else None,
                max_price=max_price if is_public else None,
            )
        )
    return result


def list_related_routes(
    db: Session,
    origin_iata: str,
    destination_iata: str,
    *,
    limit: int = 3,
) -> list[CommunityRelatedRouteOut]:
    watched = aliased(FlightWatch)
    related = aliased(FlightWatch)
    rows = db.execute(
        select(
            related.origin_iata,
            related.destination_iata,
            func.count(distinct(watched.user_id)).label("travelers_count"),
        )
        .join(related, related.user_id == watched.user_id)
        .where(
            watched.origin_iata == origin_iata,
            watched.destination_iata == destination_iata,
            watched.status != WATCH_STATUS_DELETED,
            related.status != WATCH_STATUS_DELETED,
            or_(
                related.origin_iata != origin_iata,
                related.destination_iata != destination_iata,
            ),
        )
        .group_by(related.origin_iata, related.destination_iata)
        .having(func.count(distinct(watched.user_id)) >= RELATED_ROUTE_MINIMUM_USERS)
        .order_by(
            func.count(distinct(watched.user_id)).desc(),
            related.origin_iata.asc(),
            related.destination_iata.asc(),
        )
        .limit(limit)
    ).all()
    return [
        CommunityRelatedRouteOut(
            origin_iata=related_origin,
            destination_iata=related_destination,
            travelers_count=int(travelers_count),
        )
        for related_origin, related_destination, travelers_count in rows
    ]


def _popularity_by_route(
    db: Session,
    *,
    today: Date,
) -> Mapping[RouteKey, int]:
    return {
        (origin_iata, destination_iata): int(searches_count)
        for origin_iata, destination_iata, searches_count in _popularity_rows(
            db,
            today=today,
        )
    }


def _popularity_rows(
    db: Session,
    *,
    today: Date | None = None,
) -> list[tuple[str, str, int]]:
    current_date = today or Date.today()
    start_date = current_date - timedelta(days=POPULARITY_WINDOW_DAYS - 1)
    rows = db.execute(
        select(
            QuickSearchPopularityDaily.origin_iata,
            QuickSearchPopularityDaily.destination_iata,
            func.sum(QuickSearchPopularityDaily.search_count).label("searches_count"),
        )
        .where(
            QuickSearchPopularityDaily.search_date >= start_date,
            QuickSearchPopularityDaily.search_date <= current_date,
            QuickSearchPopularityDaily.currency == "EUR",
        )
        .group_by(
            QuickSearchPopularityDaily.origin_iata,
            QuickSearchPopularityDaily.destination_iata,
        )
        .order_by(
            func.sum(QuickSearchPopularityDaily.search_count).desc(),
            QuickSearchPopularityDaily.origin_iata.asc(),
            QuickSearchPopularityDaily.destination_iata.asc(),
        )
    ).all()
    return [
        (origin_iata, destination_iata, int(searches_count))
        for origin_iata, destination_iata, searches_count in rows
        if get_airport(origin_iata) is not None
        and get_airport(destination_iata) is not None
    ]
