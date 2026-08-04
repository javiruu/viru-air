import datetime as dt

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import (
    CommunityTrendingSnapshot,
    CommunityTrendingSnapshotRoute,
    User,
    UserNotificationState,
)
from app.infrastructure.db.session import Base
from app.services.community_trending_notifier import build_community_trending_source_id
from app.services.community_trending_retention import (
    CommunityTrendingRetentionOptions,
    run_community_trending_retention,
)


def _snapshot(
    db: Session,
    *,
    snapshot_id: str,
    created_at: dt.datetime,
    status: str = "published",
    route: tuple[str, str] = ("MAD", "BCN"),
    reporting_date: dt.date | None = None,
) -> None:
    snapshot = CommunityTrendingSnapshot(
        id=snapshot_id,
        reporting_date=reporting_date or created_at.date(),
        window_start_date=created_at.date() - dt.timedelta(days=6),
        window_end_date=created_at.date(),
        calculated_at_utc=created_at,
        published_at_utc=created_at if status == "published" else None,
        expires_at_utc=created_at + dt.timedelta(hours=1),
        status=status,
        route_count=1,
        created_at=created_at,
    )
    snapshot.routes = [
        CommunityTrendingSnapshotRoute(
            id=f"route-{snapshot_id}",
            origin_iata=route[0],
            destination_iata=route[1],
            rank=1,
            search_count=20,
            created_at=created_at,
        )
    ]
    db.add(snapshot)


def _synthetic_iata(index: int) -> str:
    letters = []
    value = index
    for _ in range(3):
        letters.append(chr(ord("A") + (value % 26)))
        value //= 26
    code = "".join(reversed(letters))
    return "AAA" if code == "MAD" else code


def _db() -> tuple[object, Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_community_trending_retention_dry_run_is_non_destructive() -> None:
    engine, db = _db()
    now = dt.datetime(2026, 8, 20, 12)
    try:
        _snapshot(db, snapshot_id="old", created_at=now - dt.timedelta(days=91))
        _snapshot(db, snapshot_id="building-old", created_at=now - dt.timedelta(hours=2), status="building")
        _snapshot(db, snapshot_id="recent", created_at=now - dt.timedelta(days=89))
        db.commit()

        result = run_community_trending_retention(
            db,
            CommunityTrendingRetentionOptions(
                dry_run=True,
                batch_size=1,
                snapshot_days=90,
                now_utc=now,
            ),
        )

        assert result.published_candidates == 1
        assert result.building_candidates == 1
        assert result.deleted_total == 0
        assert db.scalar(select(func.count(CommunityTrendingSnapshot.id))) == 3
        assert db.scalar(select(func.count(CommunityTrendingSnapshotRoute.id))) == 3
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_apply_caps_sql_delete_batch_size() -> None:
    engine, db = _db()
    now = dt.datetime(2026, 8, 20, 12)
    try:
        for index in range(3):
            _snapshot(
                db,
                snapshot_id=f"large-batch-{index}",
                created_at=now - dt.timedelta(days=91, minutes=index),
            )
        db.commit()
        result = run_community_trending_retention(
            db,
            CommunityTrendingRetentionOptions(
                dry_run=False,
                batch_size=5000,
                snapshot_days=90,
                now_utc=now,
            ),
        )
        assert result.snapshots_deleted == 3
        assert result.routes_deleted == 3
        assert db.scalar(select(func.count(CommunityTrendingSnapshot.id))) == 0
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_chunks_more_than_two_hundred_state_sources() -> None:
    engine, db = _db()
    now = dt.datetime(2026, 8, 20, 12)
    try:
        user = User(
            id="user-many-community-states",
            email="many-community-states@viru.dev",
            password_hash="-",
        )
        db.add(user)
        for index in range(205):
            created_at = now - dt.timedelta(days=91, minutes=index)
            reporting_date = (now - dt.timedelta(days=91 + index)).date()
            destination = _synthetic_iata(index)
            _snapshot(
                db,
                snapshot_id=f"many-{index}",
                created_at=created_at,
                reporting_date=reporting_date,
                route=("MAD", destination),
            )
            db.add(
                UserNotificationState(
                    user_id=user.id,
                    source_type="community_trending",
                    source_id=build_community_trending_source_id(
                        reporting_date,
                        "MAD",
                        destination,
                    ),
                )
            )
        db.commit()

        result = run_community_trending_retention(
            db,
            CommunityTrendingRetentionOptions(
                dry_run=False,
                batch_size=5000,
                snapshot_days=90,
                now_utc=now,
            ),
        )

        assert result.snapshots_deleted == 205
        assert result.routes_deleted == 205
        assert result.states_deleted == 205
        assert db.scalar(select(func.count(UserNotificationState.id))) == 0
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_dry_run_handles_multiple_candidates() -> None:
    engine, db = _db()
    now = dt.datetime(2026, 8, 20, 12)
    try:
        for index in range(3):
            _snapshot(
                db,
                snapshot_id=f"old-{index}",
                created_at=now - dt.timedelta(days=91, minutes=index),
            )
        db.commit()
        result = run_community_trending_retention(
            db,
            CommunityTrendingRetentionOptions(
                dry_run=True,
                batch_size=1,
                snapshot_days=90,
                now_utc=now,
            ),
        )
        assert result.published_candidates == 3
        assert result.routes_candidates == 3
        assert result.deleted_total == 0
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_apply_removes_old_rows_and_only_community_states() -> None:
    engine, db = _db()
    now = dt.datetime(2026, 8, 20, 12)
    try:
        _snapshot(db, snapshot_id="old", created_at=now - dt.timedelta(days=91))
        _snapshot(db, snapshot_id="building-old", created_at=now - dt.timedelta(hours=2), status="building")
        _snapshot(db, snapshot_id="recent", created_at=now - dt.timedelta(days=89))
        db.add(
            User(
                id="user-1",
                email="retention@viru.dev",
                password_hash="-",
            )
        )
        db.add(
            UserNotificationState(
                user_id="user-1",
                source_type="community_trending",
                source_id="ct-20260521-MAD-BCN",
            )
        )
        db.add(
            UserNotificationState(
                user_id="user-1",
                source_type="alert_event",
                source_id="ct-20260521-MAD-BCN",
            )
        )
        db.commit()

        result = run_community_trending_retention(
            db,
            CommunityTrendingRetentionOptions(
                dry_run=False,
                batch_size=1,
                snapshot_days=90,
                now_utc=now,
            ),
        )

        assert result.snapshots_deleted == 1
        assert result.building_deleted == 1
        assert result.routes_deleted == 2
        assert result.states_deleted == 1
        assert db.get(CommunityTrendingSnapshot, "old") is None
        assert db.get(CommunityTrendingSnapshot, "building-old") is None
        assert db.get(CommunityTrendingSnapshot, "recent") is not None
        assert db.scalar(select(func.count(CommunityTrendingSnapshotRoute.id))) == 1
        states = db.scalars(select(UserNotificationState)).all()
        assert len(states) == 1
        assert {state.source_type for state in states} == {"alert_event"}
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_dry_run_counts_only_removable_duplicate_state() -> None:
    engine, db = _db()
    now = dt.datetime(2026, 8, 20, 12)
    try:
        _snapshot(db, snapshot_id="old-a", created_at=now - dt.timedelta(days=91))
        _snapshot(
            db,
            snapshot_id="recent",
            created_at=now - dt.timedelta(days=89),
            reporting_date=(now - dt.timedelta(days=91)).date(),
        )
        db.add(
            User(
                id="user-dry-run-duplicate",
                email="dry-run-duplicate@viru.dev",
                password_hash="-",
            )
        )
        db.add(
            UserNotificationState(
                user_id="user-dry-run-duplicate",
                source_type="community_trending",
                source_id="ct-20260521-MAD-BCN",
            )
        )
        db.commit()

        result = run_community_trending_retention(
            db,
            CommunityTrendingRetentionOptions(
                dry_run=True,
                batch_size=1,
                snapshot_days=90,
                now_utc=now,
            ),
        )

        assert result.states_candidates == 0
        assert result.deleted_total == 0
        assert db.scalar(select(func.count(UserNotificationState.id))) == 1
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_preserves_state_until_last_duplicate_snapshot() -> None:
    engine, db = _db()
    now = dt.datetime(2026, 8, 20, 12)
    try:
        _snapshot(db, snapshot_id="old-a", created_at=now - dt.timedelta(days=91))
        _snapshot(db, snapshot_id="old-b", created_at=now - dt.timedelta(days=91, minutes=1))
        db.add(
            User(
                id="user-duplicate",
                email="duplicate-retention@viru.dev",
                password_hash="-",
            )
        )
        db.add(
            UserNotificationState(
                user_id="user-duplicate",
                source_type="community_trending",
                source_id="ct-20260521-MAD-BCN",
            )
        )
        db.commit()
        result = run_community_trending_retention(
            db,
            CommunityTrendingRetentionOptions(
                dry_run=False,
                batch_size=1,
                snapshot_days=90,
                now_utc=now,
            ),
        )
        assert result.snapshots_deleted == 2
        assert result.states_deleted == 1
        assert db.scalars(select(UserNotificationState)).all() == []
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_rejects_invalid_building_window() -> None:
    engine, db = _db()
    try:
        with pytest.raises(ValueError, match="building_hours"):
            run_community_trending_retention(
                db,
                CommunityTrendingRetentionOptions(
                    dry_run=True,
                    batch_size=10,
                    snapshot_days=90,
                    building_hours=0,
                ),
            )
    finally:
        db.close()
        engine.dispose()


def test_community_trending_retention_rejects_unsafe_window() -> None:
    engine, db = _db()
    try:
        with pytest.raises(ValueError, match="community_trending_days"):
            run_community_trending_retention(
                db,
                CommunityTrendingRetentionOptions(
                    dry_run=True,
                    batch_size=10,
                    snapshot_days=29,
                ),
            )
    finally:
        db.close()
        engine.dispose()
