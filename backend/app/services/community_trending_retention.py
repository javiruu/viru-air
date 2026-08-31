from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import islice
from typing import Iterator

from sqlalchemy import delete, func, or_, select
from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.orm import Session

from app.core.time import utc_now_naive
from app.infrastructure.db.models import (
    CommunityTrendingSnapshot,
    CommunityTrendingSnapshotRoute,
    UserNotificationState,
)

COMMUNITY_TRENDING_RETENTION_MIN_DAYS = 30
COMMUNITY_TRENDING_BUILDING_RETENTION_HOURS = 1
# Keep DELETE/IN statements safely below SQLite's default parameter limit.
COMMUNITY_TRENDING_SQL_BATCH_SIZE = 200


def _rowcount(result: object) -> int:
    if not isinstance(result, CursorResult):
        raise RuntimeError("community_trending_delete_result_invalid")
    return result.rowcount


@dataclass(frozen=True, slots=True)
class CommunityTrendingRetentionOptions:
    dry_run: bool
    batch_size: int
    snapshot_days: int = 90
    building_hours: int = COMMUNITY_TRENDING_BUILDING_RETENTION_HOURS
    now_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class CommunityTrendingRetentionResult:
    dry_run: bool
    snapshot_days: int
    building_hours: int
    published_cutoff_utc: datetime
    building_cutoff_utc: datetime
    published_candidates: int
    building_candidates: int
    states_candidates: int
    routes_candidates: int
    snapshots_deleted: int
    building_deleted: int
    states_deleted: int
    routes_deleted: int
    batches: int
    duration_ms: float

    @property
    def candidates_total(self) -> int:
        return (
            self.published_candidates
            + self.building_candidates
            + self.states_candidates
            + self.routes_candidates
        )

    @property
    def deleted_total(self) -> int:
        return (
            self.snapshots_deleted
            + self.building_deleted
            + self.states_deleted
            + self.routes_deleted
        )

    def to_payload(self) -> dict[str, int | bool | float | str]:
        return {
            "dry_run": self.dry_run,
            "snapshot_days": self.snapshot_days,
            "building_hours": self.building_hours,
            "published_cutoff_utc": self.published_cutoff_utc.isoformat() + "Z",
            "building_cutoff_utc": self.building_cutoff_utc.isoformat() + "Z",
            "published_candidates": self.published_candidates,
            "building_candidates": self.building_candidates,
            "states_candidates": self.states_candidates,
            "routes_candidates": self.routes_candidates,
            "snapshots_deleted": self.snapshots_deleted,
            "building_deleted": self.building_deleted,
            "states_deleted": self.states_deleted,
            "routes_deleted": self.routes_deleted,
            "batches": self.batches,
            "candidates": self.candidates_total,
            "deleted": self.deleted_total,
            "duration_ms": self.duration_ms,
        }


def validate_community_trending_retention_days(days: int) -> None:
    if days < COMMUNITY_TRENDING_RETENTION_MIN_DAYS:
        raise ValueError(
            "Unsafe retention window for community_trending_days: "
            f"got {days}, requires >= {COMMUNITY_TRENDING_RETENTION_MIN_DAYS} days"
        )


def run_community_trending_retention(
    session: Session,
    options: CommunityTrendingRetentionOptions,
) -> CommunityTrendingRetentionResult:
    if options.batch_size < 1:
        raise ValueError("community trending retention batch_size must be >= 1")
    validate_community_trending_retention_days(options.snapshot_days)
    if options.building_hours <= 0:
        raise ValueError("community trending building_hours must be > 0")

    now = options.now_utc or utc_now_naive()
    published_cutoff = now - timedelta(days=options.snapshot_days)
    building_cutoff = now - timedelta(hours=options.building_hours)
    started = time.monotonic()
    candidate_status_cutoffs = (
        ("published", published_cutoff),
        ("building", building_cutoff),
    )
    published_candidates = _count_snapshot_candidates(
        session, status="published", cutoff=published_cutoff
    )
    building_candidates = _count_snapshot_candidates(
        session, status="building", cutoff=building_cutoff
    )
    candidate_source_ids, routes_candidates = _collect_candidate_metadata(
        session,
        status_cutoffs=candidate_status_cutoffs,
        batch_size=options.batch_size,
    )
    retained_source_ids = _source_ids_for_route_keys(
        session,
        candidate_source_ids,
        candidate_status_cutoffs=candidate_status_cutoffs,
    )
    removable_source_ids = candidate_source_ids - retained_source_ids
    states_candidates = _count_community_states(session, removable_source_ids)

    if options.dry_run:
        return _result(
            options=options,
            published_cutoff=published_cutoff,
            building_cutoff=building_cutoff,
            published_candidates=published_candidates,
            building_candidates=building_candidates,
            states_candidates=states_candidates,
            routes_candidates=routes_candidates,
            duration_ms=round((time.monotonic() - started) * 1000, 2),
        )

    snapshots_deleted = 0
    building_deleted = 0
    routes_deleted = 0
    batches = 0
    effective_batch_size = min(options.batch_size, COMMUNITY_TRENDING_SQL_BATCH_SIZE)
    for status, cutoff in candidate_status_cutoffs:
        for batch in _iter_candidate_batches(
            session,
            status=status,
            cutoff=cutoff,
            batch_size=effective_batch_size,
        ):
            routes_deleted += _delete_routes_for_snapshots(session, batch)
            deleted = _rowcount(session.execute(
                delete(CommunityTrendingSnapshot).where(
                    CommunityTrendingSnapshot.id.in_(batch)
                )
            ))
            session.commit()
            if status == "published":
                snapshots_deleted += deleted
            else:
                building_deleted += deleted
            batches += 1

    # Do not remove read states while another candidate batch can still represent
    # the same source. All snapshot deletion is complete at this point, so the
    # anti-join only needs to inspect snapshots that survived the retention pass.
    retained_source_ids_after_delete = _source_ids_for_route_keys(
        session,
        candidate_source_ids,
        candidate_status_cutoffs=None,
    )
    removable_source_ids_after_delete = candidate_source_ids - retained_source_ids_after_delete
    states_deleted = _delete_community_states(session, removable_source_ids_after_delete)
    session.commit()

    return _result(
        options=options,
        published_cutoff=published_cutoff,
        building_cutoff=building_cutoff,
        published_candidates=published_candidates,
        building_candidates=building_candidates,
        states_candidates=states_candidates,
        routes_candidates=routes_candidates,
        snapshots_deleted=snapshots_deleted,
        building_deleted=building_deleted,
        states_deleted=states_deleted,
        routes_deleted=routes_deleted,
        batches=batches,
        duration_ms=round((time.monotonic() - started) * 1000, 2),
    )


def _result(
    *,
    options: CommunityTrendingRetentionOptions,
    published_cutoff: datetime,
    building_cutoff: datetime,
    published_candidates: int,
    building_candidates: int,
    states_candidates: int,
    routes_candidates: int,
    snapshots_deleted: int = 0,
    building_deleted: int = 0,
    states_deleted: int = 0,
    routes_deleted: int = 0,
    batches: int = 0,
    duration_ms: float = 0,
) -> CommunityTrendingRetentionResult:
    return CommunityTrendingRetentionResult(
        dry_run=options.dry_run,
        snapshot_days=options.snapshot_days,
        building_hours=options.building_hours,
        published_cutoff_utc=published_cutoff,
        building_cutoff_utc=building_cutoff,
        published_candidates=published_candidates,
        building_candidates=building_candidates,
        states_candidates=states_candidates,
        routes_candidates=routes_candidates,
        snapshots_deleted=snapshots_deleted,
        building_deleted=building_deleted,
        states_deleted=states_deleted,
        routes_deleted=routes_deleted,
        batches=batches,
        duration_ms=duration_ms,
    )


def _count_snapshot_candidates(session: Session, *, status: str, cutoff: datetime) -> int:
    timestamp_column = (
        CommunityTrendingSnapshot.created_at
        if status == "building"
        else CommunityTrendingSnapshot.calculated_at_utc
    )
    return int(
        session.scalar(
            select(func.count(CommunityTrendingSnapshot.id)).where(
                CommunityTrendingSnapshot.status == status,
                timestamp_column < cutoff,
            )
        )
        or 0
    )


def _iter_candidate_ids(
    session: Session,
    *,
    status_cutoffs: tuple[tuple[str, datetime], ...],
    batch_size: int,
) -> Iterator[str]:
    for status, cutoff in status_cutoffs:
        timestamp_column = (
            CommunityTrendingSnapshot.created_at
            if status == "building"
            else CommunityTrendingSnapshot.calculated_at_utc
        )
        last_id: str | None = None
        while True:
            conditions = [
                CommunityTrendingSnapshot.status == status,
                timestamp_column < cutoff,
            ]
            if last_id is not None:
                conditions.append(CommunityTrendingSnapshot.id > last_id)
            ids = session.scalars(
                select(CommunityTrendingSnapshot.id)
                .where(*conditions)
                .order_by(CommunityTrendingSnapshot.id)
                .limit(batch_size)
            ).all()
            if not ids:
                break
            yield from ids
            last_id = ids[-1]
            if len(ids) < batch_size:
                break


def _iter_candidate_batches(
    session: Session,
    *,
    status: str,
    cutoff: datetime,
    batch_size: int,
) -> Iterator[list[str]]:
    timestamp_column = (
        CommunityTrendingSnapshot.created_at
        if status == "building"
        else CommunityTrendingSnapshot.calculated_at_utc
    )
    last_id: str | None = None
    while True:
        conditions = [
            CommunityTrendingSnapshot.status == status,
            timestamp_column < cutoff,
        ]
        if last_id is not None:
            conditions.append(CommunityTrendingSnapshot.id > last_id)
        ids = list(session.scalars(
            select(CommunityTrendingSnapshot.id)
            .where(*conditions)
            .order_by(CommunityTrendingSnapshot.id)
            .limit(batch_size)
        ).all())
        if not ids:
            return
        yield ids
        last_id = ids[-1]
        if len(ids) < batch_size:
            return


def _collect_candidate_metadata(
    session: Session,
    *,
    status_cutoffs: tuple[tuple[str, datetime], ...],
    batch_size: int,
) -> tuple[set[str], int]:
    candidate_ids = _iter_candidate_ids(
        session,
        status_cutoffs=status_cutoffs,
        batch_size=batch_size,
    )
    source_ids: set[str] = set()
    routes = 0
    while True:
        ids = list(islice(candidate_ids, 500))
        if not ids:
            break
        source_ids.update(_source_ids_for_snapshots(session, set(ids)))
        routes += int(
            session.scalar(
                select(func.count(CommunityTrendingSnapshotRoute.id)).where(
                    CommunityTrendingSnapshotRoute.snapshot_id.in_(ids)
                )
            )
            or 0
        )
    return source_ids, routes


def _source_ids_for_snapshots(session: Session, snapshot_ids: set[str]) -> set[str]:
    if not snapshot_ids:
        return set()
    rows = session.execute(
        select(
            CommunityTrendingSnapshot.reporting_date,
            CommunityTrendingSnapshotRoute.origin_iata,
            CommunityTrendingSnapshotRoute.destination_iata,
        )
        .join(
            CommunityTrendingSnapshotRoute,
            CommunityTrendingSnapshotRoute.snapshot_id == CommunityTrendingSnapshot.id,
        )
        .where(CommunityTrendingSnapshot.id.in_(snapshot_ids))
    ).all()
    return _source_ids_from_rows(rows)


def _source_ids_for_route_keys(
    session: Session,
    source_ids: set[str],
    *,
    candidate_status_cutoffs: tuple[tuple[str, datetime], ...] | None,
) -> set[str]:
    """Find surviving representations only for candidate source keys.

    Filtering by route keys keeps retention from loading every historical route
    into Python, while the source-id set remains bounded by candidate routes.
    """
    keys: list[tuple[date, str, str]] = []
    for source_id in source_ids:
        key = _parse_source_id(source_id)
        if key is not None:
            keys.append(key)
    retained: set[str] = set()
    for offset in range(0, len(keys), 200):
        chunk = keys[offset : offset + 200]
        route_conditions = [
            (CommunityTrendingSnapshot.reporting_date == reporting_date)
            & (CommunityTrendingSnapshotRoute.origin_iata == origin_iata)
            & (CommunityTrendingSnapshotRoute.destination_iata == destination_iata)
            for reporting_date, origin_iata, destination_iata in chunk
        ]
        conditions = [or_(*route_conditions)]
        if candidate_status_cutoffs:
            candidate_conditions = []
            for status, cutoff in candidate_status_cutoffs:
                timestamp_column = (
                    CommunityTrendingSnapshot.created_at
                    if status == "building"
                    else CommunityTrendingSnapshot.calculated_at_utc
                )
                candidate_conditions.append(
                    (CommunityTrendingSnapshot.status == status)
                    & (timestamp_column < cutoff)
                )
            conditions.append(~or_(*candidate_conditions))
        rows = session.execute(
            select(
                CommunityTrendingSnapshot.reporting_date,
                CommunityTrendingSnapshotRoute.origin_iata,
                CommunityTrendingSnapshotRoute.destination_iata,
            )
            .join(
                CommunityTrendingSnapshotRoute,
                CommunityTrendingSnapshotRoute.snapshot_id == CommunityTrendingSnapshot.id,
            )
            .where(*conditions)
        ).all()
        retained.update(_source_ids_from_rows(rows))
    return retained


def _source_ids_from_rows(rows: Sequence[Row[tuple[date, str, str]]]) -> set[str]:
    return {
        f"ct-{reporting_date:%Y%m%d}-{origin_iata}-{destination_iata}"
        for reporting_date, origin_iata, destination_iata in rows
    }


def _parse_source_id(source_id: str) -> tuple[date, str, str] | None:
    if not source_id.startswith("ct-"):
        return None
    try:
        date_raw, origin_iata, destination_iata = source_id[3:].split("-", 2)
        reporting_date = datetime.strptime(date_raw, "%Y%m%d").date()
    except (TypeError, ValueError):
        return None
    return reporting_date, origin_iata, destination_iata


def _count_community_states(session: Session, source_ids: set[str]) -> int:
    total = 0
    for chunk in _chunks(source_ids, 200):
        total += int(
            session.scalar(
                select(func.count(UserNotificationState.id)).where(
                    UserNotificationState.source_type == "community_trending",
                    UserNotificationState.source_id.in_(chunk),
                )
            )
            or 0
        )
    return total


def _delete_community_states(session: Session, source_ids: set[str]) -> int:
    deleted = 0
    for chunk in _chunks(source_ids, 200):
        deleted += _rowcount(session.execute(
            delete(UserNotificationState).where(
                UserNotificationState.source_type == "community_trending",
                UserNotificationState.source_id.in_(chunk),
            )
        ))
    return deleted


def _chunks(values: set[str], size: int) -> Iterator[set[str]]:
    values_list = list(values)
    for offset in range(0, len(values_list), size):
        yield set(values_list[offset : offset + size])


def _delete_routes_for_snapshots(session: Session, snapshot_ids: list[str]) -> int:
    return _rowcount(session.execute(
        delete(CommunityTrendingSnapshotRoute).where(
            CommunityTrendingSnapshotRoute.snapshot_id.in_(snapshot_ids)
        )
    ))
