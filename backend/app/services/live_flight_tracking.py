from __future__ import annotations

import datetime as dt
import hashlib
import logging
import re
from collections.abc import Sequence
from typing import Protocol, cast

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.live_flight_schemas import (
    LiveCoverage,
    LiveFlightIdentityOut,
    LiveFlightLegOut,
    LiveFlightMilestoneOut,
    LiveFlightOperationalOut,
    LiveFlightPositionOut,
    LiveFlightTrackingOut,
    LiveProviderStatus,
)
from app.infrastructure.db.models import (
    FlightOperationalSnapshot,
    FlightWatch,
    WatchTrackedFlightLeg,
)
from app.infrastructure.providers.operational_flight_provider import (
    OperationalFlightIdentity,
    OperationalFlightProvider,
    OperationalNoCoverage,
    OperationalNotConfigured,
    OperationalObserved,
    OperationalRateLimited,
    OperationalStatus,
    OperationalUnavailable,
)
from app.services.fare_memory_flight_instances import build_flight_instance_fingerprint
from app.services.live_flight_refresh_lock import (
    acquire_live_flight_refresh_lease,
    get_live_flight_refresh_cooldown_outcome,
    hold_live_flight_refresh_cooldown,
    release_live_flight_refresh_lease,
)
from app.services.live_flight_snapshot_retention import prune_old_operational_snapshots


logger = logging.getLogger("app.live_flight.metrics")


class TrackedLegInput(Protocol):
    flight_number: str | None
    carrier_code: str | None
    origin_iata: str
    destination_iata: str
    departure_at: dt.datetime | None
    arrival_at: dt.datetime | None


def replace_watch_tracked_legs(
    db: Session,
    watch: FlightWatch,
    legs: Sequence[TrackedLegInput] | None,
) -> str:
    existing_count = len(
        db.scalars(
            select(WatchTrackedFlightLeg.id).where(WatchTrackedFlightLeg.watch_id == watch.id)
        ).all()
    )
    if legs is None:
        return "linked" if existing_count else "missing"

    db.execute(delete(WatchTrackedFlightLeg).where(WatchTrackedFlightLeg.watch_id == watch.id))
    for sequence, leg in enumerate(legs):
        carrier_code = leg.carrier_code or _carrier_code_from_flight_number(leg.flight_number)
        fingerprint = build_flight_instance_fingerprint(
            {
                "provider": "watchlist",
                "carrier_code": carrier_code,
                "flight_number": leg.flight_number,
                "origin_airport": leg.origin_iata,
                "destination_airport": leg.destination_iata,
                "departure_at": leg.departure_at,
                "arrival_at": leg.arrival_at,
                "stops_count": 0,
            }
        )
        db.add(
            WatchTrackedFlightLeg(
                watch_id=watch.id,
                sequence=sequence,
                flight_instance_fingerprint=fingerprint,
                carrier_code=carrier_code,
                flight_number=leg.flight_number,
                origin_iata=leg.origin_iata,
                destination_iata=leg.destination_iata,
                departure_date_local=leg.departure_at.date() if leg.departure_at else None,
                scheduled_departure_at=_utc_naive_if_aware(leg.departure_at),
                scheduled_arrival_at=_utc_naive_if_aware(leg.arrival_at),
                identity_source="quick_search",
            )
        )
    return "updated" if existing_count else "linked" if legs else "missing"


def refresh_live_tracking(
    db: Session,
    watch: FlightWatch,
    provider: OperationalFlightProvider | OperationalNotConfigured,
    refresh: bool,
) -> str | None:
    legs = list(
        db.scalars(
            select(WatchTrackedFlightLeg)
            .where(WatchTrackedFlightLeg.watch_id == watch.id)
            .order_by(WatchTrackedFlightLeg.sequence)
        ).all()
    )
    if not refresh or not legs:
        return None
    if isinstance(provider, OperationalNotConfigured):
        logger.info("live_flight_refresh outcome=not_configured")
        return "not_configured"
    now = utc_now_naive()
    provider_status: str | None = None
    user_lease = None
    user_refresh_key = hashlib.sha256(f"live-user:{watch.user_id}".encode()).hexdigest()
    for leg in legs:
        fresh_snapshot = db.scalar(
            select(FlightOperationalSnapshot)
            .where(
                FlightOperationalSnapshot.flight_instance_fingerprint == leg.flight_instance_fingerprint,
                FlightOperationalSnapshot.expires_at >= now,
            )
            .order_by(FlightOperationalSnapshot.observed_at.desc())
            .limit(1)
        )
        if fresh_snapshot is not None:
            logger.info("live_flight_refresh outcome=cache_hit")
            continue
        cooldown_outcome = get_live_flight_refresh_cooldown_outcome(
            db,
            flight_instance_fingerprint=leg.flight_instance_fingerprint,
            now=now,
        )
        if cooldown_outcome is not None:
            provider_status = cooldown_outcome
            logger.info("live_flight_refresh outcome=cooldown_hit")
            continue
        if user_lease is None:
            user_lease = acquire_live_flight_refresh_lease(
                db,
                flight_instance_fingerprint=user_refresh_key,
                now=now,
                ttl_seconds=30,
            )
            if user_lease is None:
                provider_status = "unavailable"
                logger.info("live_flight_refresh outcome=user_cooldown")
                continue
        lease = acquire_live_flight_refresh_lease(
            db,
            flight_instance_fingerprint=leg.flight_instance_fingerprint,
            now=now,
        )
        if lease is None:
            provider_status = get_live_flight_refresh_cooldown_outcome(
                db,
                flight_instance_fingerprint=leg.flight_instance_fingerprint,
                now=now,
            ) or "unavailable"
            logger.info("live_flight_refresh outcome=singleflight_busy")
            continue
        release_lease = True
        try:
            outcome = provider.fetch(_identity_from_leg(leg), now)
            if isinstance(outcome, OperationalObserved):
                snapshot = _snapshot_from_observation(leg, outcome.observation)
                duplicate = db.scalar(
                    select(FlightOperationalSnapshot.id).where(
                        FlightOperationalSnapshot.flight_instance_fingerprint
                        == snapshot.flight_instance_fingerprint,
                        FlightOperationalSnapshot.provider == snapshot.provider,
                        FlightOperationalSnapshot.observed_at == snapshot.observed_at,
                    )
                )
                if duplicate is None:
                    db.add(snapshot)
                    try:
                        db.commit()
                    except IntegrityError:
                        db.rollback()
                prune_old_operational_snapshots(db, now=now)
                provider_status = "ok"
                logger.info("live_flight_refresh outcome=observed")
            elif isinstance(outcome, OperationalNoCoverage):
                provider_status = outcome.reason
                release_lease = not hold_live_flight_refresh_cooldown(
                    db,
                    lock_token=lease.lock_token,
                    outcome=outcome.reason,
                    now=now,
                    ttl_seconds=300,
                )
                logger.info("live_flight_refresh outcome=%s", outcome.reason)
            elif isinstance(outcome, OperationalRateLimited):
                provider_status = "rate_limited"
                release_lease = not hold_live_flight_refresh_cooldown(
                    db,
                    lock_token=lease.lock_token,
                    outcome="rate_limited",
                    now=now,
                    ttl_seconds=max(30, min(3600, outcome.retry_after_seconds)),
                )
                logger.info("live_flight_refresh outcome=rate_limited")
            elif isinstance(outcome, OperationalUnavailable):
                provider_status = "unavailable"
                release_lease = not hold_live_flight_refresh_cooldown(
                    db,
                    lock_token=lease.lock_token,
                    outcome="unavailable",
                    now=now,
                    ttl_seconds=60,
                )
                logger.info("live_flight_refresh outcome=unavailable reason=%s", outcome.reason)
            elif isinstance(outcome, OperationalNotConfigured):
                provider_status = "not_configured"
                release_lease = not hold_live_flight_refresh_cooldown(
                    db,
                    lock_token=lease.lock_token,
                    outcome="not_configured",
                    now=now,
                    ttl_seconds=3600,
                )
                logger.info("live_flight_refresh outcome=not_configured")
        finally:
            if release_lease:
                release_live_flight_refresh_lease(db, lock_token=lease.lock_token)
    if user_lease is not None:
        held = hold_live_flight_refresh_cooldown(
            db,
            lock_token=user_lease.lock_token,
            outcome="user_cooldown",
            now=now,
            ttl_seconds=30,
        )
        if not held:
            release_live_flight_refresh_lease(db, lock_token=user_lease.lock_token)
    return provider_status


def build_live_tracking_response(
    db: Session,
    watch: FlightWatch,
    provider_status_override: str | None = None,
) -> LiveFlightTrackingOut:
    legs = list(
        db.scalars(
            select(WatchTrackedFlightLeg)
            .where(WatchTrackedFlightLeg.watch_id == watch.id)
            .order_by(WatchTrackedFlightLeg.sequence)
        ).all()
    )
    if not legs:
        return LiveFlightTrackingOut(
            watch_id=watch.id,
            coverage="identity_missing",
            provider_status="no_match",
            generated_at=utc_now_naive(),
            refresh_after_seconds=3600,
            legs=[],
        )
    now = utc_now_naive()
    fingerprints = {leg.flight_instance_fingerprint for leg in legs}
    snapshots = list(
        db.scalars(
            select(FlightOperationalSnapshot)
            .where(FlightOperationalSnapshot.flight_instance_fingerprint.in_(fingerprints))
            .order_by(
                FlightOperationalSnapshot.observed_at.desc(),
                FlightOperationalSnapshot.id.desc(),
            )
        ).all()
    )
    latest_by_fingerprint: dict[str, FlightOperationalSnapshot] = {}
    for snapshot in snapshots:
        latest_by_fingerprint.setdefault(snapshot.flight_instance_fingerprint, snapshot)
    has_fresh = any(snapshot.expires_at >= now for snapshot in latest_by_fingerprint.values())
    has_cached = bool(latest_by_fingerprint)
    all_terminal = len(latest_by_fingerprint) == len(legs) and all(
        snapshot.status in {"landed", "cancelled", "diverted"}
        for snapshot in latest_by_fingerprint.values()
    )
    coverage: LiveCoverage = (
        "completed"
        if all_terminal
        else "live"
        if has_fresh
        else "cached"
        if has_cached
        else "not_configured"
    )
    provider_status = "ok" if has_fresh else _provider_status(provider_status_override)
    if not has_cached and provider_status in {"no_match", "ambiguous"}:
        coverage = "no_coverage"
    elif not has_fresh and provider_status in {"rate_limited", "unavailable"}:
        coverage = "temporarily_unavailable"
    refresh_after_seconds = min(
        (_refresh_after_seconds(leg, latest_by_fingerprint.get(leg.flight_instance_fingerprint), now) for leg in legs),
        default=3600,
    )
    return LiveFlightTrackingOut(
        watch_id=watch.id,
        coverage=coverage,
        provider_status=provider_status,
        generated_at=now,
        refresh_after_seconds=refresh_after_seconds,
        legs=[
            LiveFlightLegOut(
                sequence=leg.sequence,
                identity=LiveFlightIdentityOut(
                    flight_instance_fingerprint=leg.flight_instance_fingerprint,
                    flight_number=leg.flight_number,
                    carrier_code=leg.carrier_code,
                    origin_iata=leg.origin_iata,
                    destination_iata=leg.destination_iata,
                    scheduled_departure_at=leg.scheduled_departure_at,
                    scheduled_arrival_at=leg.scheduled_arrival_at,
                ),
                operational=_snapshot_out(
                    latest_by_fingerprint.get(leg.flight_instance_fingerprint),
                    now,
                ),
            )
            for leg in legs
        ],
    )


def _identity_from_leg(leg: WatchTrackedFlightLeg) -> OperationalFlightIdentity:
    return OperationalFlightIdentity(
        flight_instance_fingerprint=leg.flight_instance_fingerprint,
        flight_number=leg.flight_number,
        carrier_code=leg.carrier_code,
        origin_iata=leg.origin_iata,
        destination_iata=leg.destination_iata,
        departure_date_local=leg.departure_date_local,
        scheduled_departure_at=leg.scheduled_departure_at,
        scheduled_arrival_at=leg.scheduled_arrival_at,
    )


def _snapshot_from_observation(
    leg: WatchTrackedFlightLeg,
    observation,
) -> FlightOperationalSnapshot:
    return FlightOperationalSnapshot(
        flight_instance_fingerprint=leg.flight_instance_fingerprint,
        provider=observation.provider,
        provider_flight_id=observation.provider_flight_id,
        flight_number=observation.flight_number,
        callsign=observation.callsign,
        icao24=observation.icao24,
        status=observation.status,
        status_raw=observation.status_raw,
        observed_at=observation.observed_at,
        expires_at=observation.expires_at,
        scheduled_departure_at=observation.scheduled_departure_at,
        estimated_departure_at=observation.estimated_departure_at,
        actual_departure_at=observation.actual_departure_at,
        scheduled_arrival_at=observation.scheduled_arrival_at,
        estimated_arrival_at=observation.estimated_arrival_at,
        actual_arrival_at=observation.actual_arrival_at,
        departure_terminal=observation.departure_terminal,
        departure_gate=observation.departure_gate,
        arrival_terminal=observation.arrival_terminal,
        arrival_gate=observation.arrival_gate,
        departure_delay_minutes=observation.departure_delay_minutes,
        arrival_delay_minutes=observation.arrival_delay_minutes,
        latitude=observation.latitude,
        longitude=observation.longitude,
        altitude_m=observation.altitude_m,
        speed_mps=observation.speed_mps,
        heading_deg=observation.heading_deg,
        on_ground=observation.on_ground,
        registration=observation.registration,
        aircraft_iata=observation.aircraft_iata,
        aircraft_icao=observation.aircraft_icao,
        data_quality=observation.data_quality,
    )


def _snapshot_out(
    snapshot: FlightOperationalSnapshot | None,
    now: dt.datetime,
) -> LiveFlightOperationalOut | None:
    if snapshot is None:
        return None
    position = None
    if snapshot.latitude is not None and snapshot.longitude is not None:
        position = LiveFlightPositionOut(
            latitude=float(snapshot.latitude),
            longitude=float(snapshot.longitude),
            altitude_m=float(snapshot.altitude_m) if snapshot.altitude_m is not None else None,
            speed_mps=float(snapshot.speed_mps) if snapshot.speed_mps is not None else None,
            heading_deg=float(snapshot.heading_deg) if snapshot.heading_deg is not None else None,
            on_ground=snapshot.on_ground,
        )
    return LiveFlightOperationalOut(
        status=_operational_status(snapshot.status),
        status_raw=snapshot.status_raw,
        observed_at=snapshot.observed_at,
        expires_at=snapshot.expires_at,
        freshness="fresh" if snapshot.expires_at >= now else "stale",
        provider=snapshot.provider,
        callsign=snapshot.callsign,
        departure=LiveFlightMilestoneOut(
            scheduled_at=snapshot.scheduled_departure_at,
            estimated_at=snapshot.estimated_departure_at,
            actual_at=snapshot.actual_departure_at,
            terminal=snapshot.departure_terminal,
            gate=snapshot.departure_gate,
            delay_minutes=snapshot.departure_delay_minutes,
        ),
        arrival=LiveFlightMilestoneOut(
            scheduled_at=snapshot.scheduled_arrival_at,
            estimated_at=snapshot.estimated_arrival_at,
            actual_at=snapshot.actual_arrival_at,
            terminal=snapshot.arrival_terminal,
            gate=snapshot.arrival_gate,
            delay_minutes=snapshot.arrival_delay_minutes,
        ),
        position=position,
        registration=snapshot.registration,
        aircraft_iata=snapshot.aircraft_iata,
        aircraft_icao=snapshot.aircraft_icao,
        data_quality=snapshot.data_quality,
    )


def _refresh_after_seconds(
    leg: WatchTrackedFlightLeg,
    snapshot: FlightOperationalSnapshot | None,
    now: dt.datetime,
) -> int:
    if snapshot is not None and snapshot.status == "active":
        return 60
    if snapshot is not None and snapshot.status in {"landed", "cancelled", "diverted"}:
        return 21600
    departure_at = leg.scheduled_departure_at
    if departure_at is None:
        return 3600
    seconds_until_departure = (departure_at - now).total_seconds()
    if seconds_until_departure <= 7200:
        return 300
    if seconds_until_departure <= 86400:
        return 1800
    return 21600


def _carrier_code_from_flight_number(flight_number: str | None) -> str | None:
    if not flight_number:
        return None
    match = re.match(r"^([A-Z0-9]{2,3})\s*\d", flight_number.strip().upper())
    return match.group(1) if match else None


def _utc_naive_if_aware(value: dt.datetime | None) -> dt.datetime | None:
    if value is None or value.tzinfo is None:
        return None
    return value.astimezone(dt.UTC).replace(tzinfo=None)


def _provider_status(value: str | None) -> LiveProviderStatus:
    if value in {
        "ok",
        "not_configured",
        "no_match",
        "ambiguous",
        "rate_limited",
        "unavailable",
    }:
        return cast(LiveProviderStatus, value)
    return "not_configured"


def _operational_status(value: str) -> OperationalStatus:
    if value in {"scheduled", "active", "landed", "cancelled", "diverted"}:
        return cast(OperationalStatus, value)
    return "unknown"
