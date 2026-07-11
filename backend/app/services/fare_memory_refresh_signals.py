from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Final, TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.vocabulary import WATCH_STATUS_ACTIVE
from app.infrastructure.db.models import AlertRule, FlightWatch, QuickSearchPopularityCounter

_RECENT_SEARCH_WINDOW_DAYS: Final = 30
_WATCH_SIGNAL_WEIGHT: Final = 30
_ALERT_SIGNAL_WEIGHT: Final = 35
_SEARCH_SIGNAL_WEIGHT: Final = 2
_MAX_SEARCH_SIGNAL_COUNT: Final = 50
_BASE_REVALIDATION_PRIORITY: Final = 500


class RouteRefreshSignalPayload(TypedDict):
    route: str
    origin_iata: str
    destination_iata: str
    travel_date: str
    active_watch_count: int
    enabled_alert_count: int
    recent_search_count: int
    days_until_departure: int
    priority_score: int
    suggested_job_priority: int
    reasons: list[str]


@dataclass(frozen=True, slots=True, order=True)
class RouteRefreshKey:
    origin_iata: str
    destination_iata: str
    travel_date: dt.date


@dataclass(frozen=True, slots=True)
class RouteSignalCount:
    key: RouteRefreshKey
    value: int


@dataclass(frozen=True, slots=True)
class RouteSignalInputs:
    active_watch_count: int
    enabled_alert_count: int
    recent_search_count: int
    days_until_departure: int


@dataclass(frozen=True, slots=True)
class RouteRefreshSignals:
    origin_iata: str
    destination_iata: str
    travel_date: dt.date
    active_watch_count: int
    enabled_alert_count: int
    recent_search_count: int
    days_until_departure: int
    priority_score: int
    suggested_job_priority: int
    reasons: tuple[str, ...]

    @property
    def route(self) -> str:
        return f"{self.origin_iata}-{self.destination_iata}"

    def to_payload(self) -> RouteRefreshSignalPayload:
        return {
            "route": self.route,
            "origin_iata": self.origin_iata,
            "destination_iata": self.destination_iata,
            "travel_date": self.travel_date.isoformat(),
            "active_watch_count": self.active_watch_count,
            "enabled_alert_count": self.enabled_alert_count,
            "recent_search_count": self.recent_search_count,
            "days_until_departure": self.days_until_departure,
            "priority_score": self.priority_score,
            "suggested_job_priority": self.suggested_job_priority,
            "reasons": list(self.reasons),
        }


def build_route_refresh_signals(
    db: Session,
    *,
    now: dt.datetime | None = None,
    limit: int = 25,
) -> list[RouteRefreshSignals]:
    reference_now = now or utc_now_naive()
    today = reference_now.date()
    active_watch_counts = {
        route_count.key: route_count.value
        for route_count in _active_watch_counts(db, today=today)
    }
    enabled_alert_counts = {
        route_count.key: route_count.value
        for route_count in _enabled_alert_counts(db, today=today)
    }
    recent_search_counts = {
        route_count.key: route_count.value
        for route_count in _recent_search_counts(db, now=reference_now)
    }
    keys = set(active_watch_counts) | set(enabled_alert_counts) | set(recent_search_counts)

    signals = [
        _build_route_refresh_signal(
            key,
            RouteSignalInputs(
                active_watch_count=active_watch_counts.get(key, 0),
                enabled_alert_count=enabled_alert_counts.get(key, 0),
                recent_search_count=recent_search_counts.get(key, 0),
                days_until_departure=max(0, (key.travel_date - today).days),
            ),
        )
        for key in keys
    ]
    return sorted(
        signals,
        key=lambda signal: (
            -signal.priority_score,
            signal.suggested_job_priority,
            signal.days_until_departure,
            signal.travel_date,
            signal.origin_iata,
            signal.destination_iata,
        ),
    )[: max(0, int(limit))]


def _active_watch_counts(db: Session, *, today: dt.date) -> list[RouteSignalCount]:
    rows = db.execute(
        select(
            FlightWatch.origin_iata,
            FlightWatch.destination_iata,
            FlightWatch.travel_date_local,
            func.count(FlightWatch.id),
        )
        .where(FlightWatch.status == WATCH_STATUS_ACTIVE)
        .where(FlightWatch.travel_date_local >= today)
        .group_by(
            FlightWatch.origin_iata,
            FlightWatch.destination_iata,
            FlightWatch.travel_date_local,
        )
    ).all()
    return [
        RouteSignalCount(
            key=RouteRefreshKey(
                origin_iata=str(origin_iata).upper(),
                destination_iata=str(destination_iata).upper(),
                travel_date=travel_date,
            ),
            value=int(watch_count),
        )
        for origin_iata, destination_iata, travel_date, watch_count in rows
    ]


def _enabled_alert_counts(db: Session, *, today: dt.date) -> list[RouteSignalCount]:
    rows = db.execute(
        select(
            FlightWatch.origin_iata,
            FlightWatch.destination_iata,
            FlightWatch.travel_date_local,
            func.count(AlertRule.id),
        )
        .join(FlightWatch, FlightWatch.id == AlertRule.watch_id)
        .where(FlightWatch.status == WATCH_STATUS_ACTIVE)
        .where(FlightWatch.travel_date_local >= today)
        .where(AlertRule.enabled.is_(True))
        .group_by(
            FlightWatch.origin_iata,
            FlightWatch.destination_iata,
            FlightWatch.travel_date_local,
        )
    ).all()
    return [
        RouteSignalCount(
            key=RouteRefreshKey(
                origin_iata=str(origin_iata).upper(),
                destination_iata=str(destination_iata).upper(),
                travel_date=travel_date,
            ),
            value=int(alert_count),
        )
        for origin_iata, destination_iata, travel_date, alert_count in rows
    ]


def _recent_search_counts(db: Session, *, now: dt.datetime) -> list[RouteSignalCount]:
    recent_from = now - dt.timedelta(days=_RECENT_SEARCH_WINDOW_DAYS)
    rows = db.execute(
        select(
            QuickSearchPopularityCounter.origin_iata,
            QuickSearchPopularityCounter.destination_iata,
            QuickSearchPopularityCounter.travel_date,
            func.sum(QuickSearchPopularityCounter.search_count),
        )
        .where(QuickSearchPopularityCounter.travel_date >= now.date())
        .where(QuickSearchPopularityCounter.last_searched_at >= recent_from)
        .group_by(
            QuickSearchPopularityCounter.origin_iata,
            QuickSearchPopularityCounter.destination_iata,
            QuickSearchPopularityCounter.travel_date,
        )
    ).all()
    return [
        RouteSignalCount(
            key=RouteRefreshKey(
                origin_iata=str(origin_iata).upper(),
                destination_iata=str(destination_iata).upper(),
                travel_date=travel_date,
            ),
            value=int(search_count or 0),
        )
        for origin_iata, destination_iata, travel_date, search_count in rows
    ]


def _build_route_refresh_signal(
    key: RouteRefreshKey,
    inputs: RouteSignalInputs,
) -> RouteRefreshSignals:
    priority_score = _priority_score(inputs)
    return RouteRefreshSignals(
        origin_iata=key.origin_iata,
        destination_iata=key.destination_iata,
        travel_date=key.travel_date,
        active_watch_count=inputs.active_watch_count,
        enabled_alert_count=inputs.enabled_alert_count,
        recent_search_count=inputs.recent_search_count,
        days_until_departure=inputs.days_until_departure,
        priority_score=priority_score,
        suggested_job_priority=max(1, _BASE_REVALIDATION_PRIORITY - priority_score),
        reasons=_reasons(inputs),
    )


def _priority_score(inputs: RouteSignalInputs) -> int:
    search_count = min(inputs.recent_search_count, _MAX_SEARCH_SIGNAL_COUNT)
    return (
        inputs.active_watch_count * _WATCH_SIGNAL_WEIGHT
        + inputs.enabled_alert_count * _ALERT_SIGNAL_WEIGHT
        + search_count * _SEARCH_SIGNAL_WEIGHT
        + _departure_bonus(inputs.days_until_departure)
    )


def _departure_bonus(days_until_departure: int) -> int:
    if days_until_departure <= 3:
        return 40
    if days_until_departure <= 7:
        return 25
    if days_until_departure <= 14:
        return 15
    if days_until_departure <= 30:
        return 5
    return 0


def _reasons(inputs: RouteSignalInputs) -> tuple[str, ...]:
    reasons: list[str] = []
    if inputs.active_watch_count > 0:
        reasons.append("active_watchlist")
    if inputs.enabled_alert_count > 0:
        reasons.append("enabled_alerts")
    if inputs.recent_search_count > 0:
        reasons.append("recent_searches")
    if inputs.days_until_departure <= 14:
        reasons.append("departure_near")
    return tuple(reasons)
