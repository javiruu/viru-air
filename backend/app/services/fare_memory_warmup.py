from __future__ import annotations

import json
import logging
import random
from dataclasses import asdict, dataclass
from datetime import date as date_type, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.domain.vocabulary import WATCH_STATUS_ACTIVE
from app.infrastructure.db.models import AlertRule, FlightWatch, PriceSnapshot, RevalidationJob
from app.services.revalidation_jobs import ACTIVE_REVALIDATION_JOB_STATUSES, enqueue_revalidation_job

logger = logging.getLogger("app.fare_memory.warmup")

_WARMUP_THRESHOLD_NEAR_RATIO = 0.15
_WARMUP_DEPARTURE_SOON_DAYS = 14


@dataclass(slots=True)
class BootWarmupCandidate:
    watch_id: str
    origin_iata: str
    destination_iata: str
    travel_date_local: str
    priority: int
    enabled_alert_count: int
    latest_price: float | None
    latest_currency: str | None
    latest_snapshot_age_seconds: int | None
    latest_snapshot_is_stale: bool
    departure_in_days: int
    near_threshold: bool
    threshold_distance_ratio: float | None
    reasons: list[str]


def build_boot_warmup_candidate_report(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 25,
) -> dict[str, object]:
    reference_now = now or utc_now_naive()
    computed_candidates = _compute_boot_warmup_candidates(db, now=reference_now)
    selected_candidates = computed_candidates[: max(0, int(limit))]
    return {
        "event": "fare_memory_boot_warmup_dry_run",
        "mode": "dry_run",
        "enabled": True,
        "candidate_count": len(selected_candidates),
        "total_candidate_count": len(computed_candidates),
        "skipped_candidate_count": max(0, len(computed_candidates) - len(selected_candidates)),
        "limit": max(0, int(limit)),
        "generated_at": reference_now.isoformat(),
        "candidates": [asdict(candidate) for candidate in selected_candidates],
    }


def log_boot_warmup_dry_run(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 25,
) -> dict[str, object]:
    report = build_boot_warmup_candidate_report(db, now=now, limit=limit)
    logger.info(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


def schedule_boot_warmup_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 25,
    provider_rate_limit_per_minute: int = 60,
    jitter_seconds: int = 30,
    provider: str = "multi",
    rng: random.Random | None = None,
) -> dict[str, object]:
    reference_now = now or utc_now_naive()
    computed_candidates = _compute_boot_warmup_candidates(db, now=reference_now)
    allowed_job_count = max(0, min(int(limit), max(0, int(provider_rate_limit_per_minute))))
    selected_candidates = computed_candidates[:allowed_job_count]
    skipped_due_rate_limit = max(0, len(computed_candidates) - len(selected_candidates))
    random_source = rng or random.Random()
    queued_jobs: list[dict[str, object]] = []
    enqueued_job_count = 0
    skipped_due_lock_count = 0

    for candidate in selected_candidates:
        target_fingerprint = _route_target_fingerprint(candidate)
        active_job = _find_active_revalidation_job(
            db,
            target_type="route",
            target_fingerprint=target_fingerprint,
            provider=provider,
        )
        if active_job is not None:
            skipped_due_lock_count += 1
            queued_jobs.append(
                {
                    "watch_id": candidate.watch_id,
                    "job_id": active_job.id,
                    "scheduled_at": active_job.scheduled_at.isoformat(),
                    "target_fingerprint": target_fingerprint,
                    "status": "duplicate_locked",
                }
            )
            continue

        jitter_offset_seconds = random_source.randint(0, max(0, int(jitter_seconds)))
        scheduled_at = reference_now + timedelta(seconds=jitter_offset_seconds)
        job, created = enqueue_revalidation_job(
            db,
            job_type="boot_warmup",
            target_type="route",
            target_fingerprint=target_fingerprint,
            provider=provider,
            priority=candidate.priority,
            scheduled_at=scheduled_at,
            payload={
                "watch_id": candidate.watch_id,
                "origin_iata": candidate.origin_iata,
                "destination_iata": candidate.destination_iata,
                "travel_date_local": candidate.travel_date_local,
                "reasons": candidate.reasons,
            },
        )
        if created:
            enqueued_job_count += 1
            queued_jobs.append(
                {
                    "watch_id": candidate.watch_id,
                    "job_id": job.id,
                    "scheduled_at": job.scheduled_at.isoformat(),
                    "target_fingerprint": job.target_fingerprint,
                    "status": job.status,
                }
            )
            continue

        skipped_due_lock_count += 1
        queued_jobs.append(
            {
                "watch_id": candidate.watch_id,
                "job_id": job.id,
                "scheduled_at": job.scheduled_at.isoformat(),
                "target_fingerprint": job.target_fingerprint,
                "status": "duplicate_locked",
            }
        )

    return {
        "event": "fare_memory_boot_warmup_scheduled",
        "mode": "controlled",
        "enabled": True,
        "candidate_count": len(selected_candidates),
        "total_candidate_count": len(computed_candidates),
        "limit": int(limit),
        "provider_rate_limit_per_minute": int(provider_rate_limit_per_minute),
        "jitter_seconds": max(0, int(jitter_seconds)),
        "enqueued_job_count": enqueued_job_count,
        "skipped_due_lock_count": skipped_due_lock_count,
        "warmup_jobs_skipped_due_rate_limit": skipped_due_rate_limit,
        "generated_at": reference_now.isoformat(),
        "jobs": queued_jobs,
    }


def log_scheduled_boot_warmup_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 25,
    provider_rate_limit_per_minute: int = 60,
    jitter_seconds: int = 30,
    provider: str = "multi",
    rng: random.Random | None = None,
) -> dict[str, object]:
    report = schedule_boot_warmup_jobs(
        db,
        now=now,
        limit=limit,
        provider_rate_limit_per_minute=provider_rate_limit_per_minute,
        jitter_seconds=jitter_seconds,
        provider=provider,
        rng=rng,
    )
    logger.info(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


def _compute_boot_warmup_candidates(
    db: Session,
    *,
    now: datetime,
) -> list[BootWarmupCandidate]:
    latest_snapshot_by_watch = _latest_snapshot_by_watch(db)
    alerts_by_watch = _enabled_alerts_by_watch(db)

    candidates: list[BootWarmupCandidate] = []
    watches = db.scalars(
        select(FlightWatch)
        .where(FlightWatch.status == WATCH_STATUS_ACTIVE)
        .order_by(FlightWatch.travel_date_local.asc(), FlightWatch.created_at.asc(), FlightWatch.id.asc())
    ).all()

    for watch in watches:
        latest_snapshot = latest_snapshot_by_watch.get(watch.id)
        alerts = alerts_by_watch.get(watch.id, [])
        candidates.append(
            _build_candidate(
                watch=watch,
                alerts=alerts,
                latest_snapshot=latest_snapshot,
                now=now,
            )
        )

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.priority,
            candidate.departure_in_days,
            candidate.travel_date_local,
            candidate.watch_id,
        ),
    )


def _latest_snapshot_by_watch(db: Session) -> dict[str, PriceSnapshot]:
    rows = db.scalars(
        select(PriceSnapshot)
        .order_by(
            PriceSnapshot.watch_id.asc(),
            PriceSnapshot.captured_at_utc.desc(),
            PriceSnapshot.id.desc(),
        )
    ).all()

    latest_by_watch: dict[str, PriceSnapshot] = {}
    for snapshot in rows:
        latest_by_watch.setdefault(snapshot.watch_id, snapshot)
    return latest_by_watch


def _enabled_alerts_by_watch(db: Session) -> dict[str, list[AlertRule]]:
    alerts_by_watch: dict[str, list[AlertRule]] = {}
    rows = db.scalars(
        select(AlertRule)
        .where(AlertRule.enabled.is_(True))
        .order_by(AlertRule.watch_id.asc(), AlertRule.id.asc())
    ).all()
    for alert in rows:
        alerts_by_watch.setdefault(alert.watch_id, []).append(alert)
    return alerts_by_watch


def _build_candidate(
    *,
    watch: FlightWatch,
    alerts: list[AlertRule],
    latest_snapshot: PriceSnapshot | None,
    now: datetime,
) -> BootWarmupCandidate:
    latest_price = float(latest_snapshot.raw_price) if latest_snapshot is not None else None
    latest_currency = latest_snapshot.raw_currency if latest_snapshot is not None else None
    latest_snapshot_age_seconds = _snapshot_age_seconds(latest_snapshot, now=now)
    departure_in_days = max(0, _days_until_departure(watch.travel_date_local, now=now))
    threshold_distance_ratio = _nearest_threshold_distance_ratio(alerts, latest_price)
    near_threshold = threshold_distance_ratio is not None and threshold_distance_ratio <= _WARMUP_THRESHOLD_NEAR_RATIO

    reasons: list[str] = []
    priority = 500

    if alerts:
        priority -= 200
        reasons.append("active_alert_enabled")
    if latest_snapshot is not None and latest_snapshot.is_stale:
        priority -= 120
        reasons.append("stale_snapshot")
    if near_threshold:
        closeness_bonus = int(round((_WARMUP_THRESHOLD_NEAR_RATIO - threshold_distance_ratio) * 100))
        priority -= 100 + max(0, closeness_bonus)
        reasons.append("near_alert_threshold")
    if departure_in_days <= _WARMUP_DEPARTURE_SOON_DAYS:
        priority -= 80
        reasons.append("departure_soon")
    if latest_snapshot is None:
        priority -= 40
        reasons.append("missing_snapshot")

    return BootWarmupCandidate(
        watch_id=watch.id,
        origin_iata=watch.origin_iata,
        destination_iata=watch.destination_iata,
        travel_date_local=watch.travel_date_local.isoformat(),
        priority=priority,
        enabled_alert_count=len(alerts),
        latest_price=latest_price,
        latest_currency=latest_currency,
        latest_snapshot_age_seconds=latest_snapshot_age_seconds,
        latest_snapshot_is_stale=bool(latest_snapshot.is_stale) if latest_snapshot is not None else False,
        departure_in_days=departure_in_days,
        near_threshold=near_threshold,
        threshold_distance_ratio=threshold_distance_ratio,
        reasons=reasons or ["active_watch"],
    )


def _snapshot_age_seconds(snapshot: PriceSnapshot | None, *, now: datetime) -> int | None:
    if snapshot is None:
        return None
    delta = now - snapshot.captured_at_utc
    return max(0, int(delta.total_seconds()))


def _days_until_departure(travel_date_local: date_type, *, now: datetime) -> int:
    return (travel_date_local - now.date()).days


def _nearest_threshold_distance_ratio(alerts: list[AlertRule], latest_price: float | None) -> float | None:
    if latest_price is None:
        return None

    candidate_ratios: list[float] = []
    for alert in alerts:
        if alert.threshold_value in (None, Decimal("0")):
            continue
        threshold_value = float(alert.threshold_value)
        if threshold_value <= 0:
            continue
        candidate_ratios.append(abs(latest_price - threshold_value) / threshold_value)

    if not candidate_ratios:
        return None
    return min(candidate_ratios)


def _route_target_fingerprint(candidate: BootWarmupCandidate) -> str:
    return (
        f"route:{candidate.origin_iata}:{candidate.destination_iata}:{candidate.travel_date_local}"
    )


def _find_active_revalidation_job(
    db: Session,
    *,
    target_type: str,
    target_fingerprint: str,
    provider: str | None,
) -> RevalidationJob | None:
    return db.scalar(
        select(RevalidationJob)
        .where(RevalidationJob.target_type == target_type)
        .where(RevalidationJob.target_fingerprint == target_fingerprint)
        .where(RevalidationJob.provider == provider)
        .where(RevalidationJob.status.in_(tuple(ACTIVE_REVALIDATION_JOB_STATUSES)))
        .order_by(RevalidationJob.created_at.desc(), RevalidationJob.id.desc())
        .limit(1)
    )
