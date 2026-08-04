from collections.abc import Generator
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import (
    CommunityTrendingSnapshot,
    CommunityTrendingSnapshotRoute,
    QuickSearchPopularityDaily,
)
from app.infrastructure.db.session import get_db
from app.main import app
from app.services.community_trending_notifier import notify_trending_routes
from tests.helpers import register_and_token


def _open_db() -> tuple[Session, Generator[Session, None, None]]:
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    return db, generator


def _close_db(db: Session, generator: Generator[Session, None, None]) -> None:
    db.close()
    try:
        next(generator)
    except StopIteration:
        return


def _seed_route(
    origin: str,
    destination: str,
    count: int,
    *,
    search_date: date,
) -> None:
    db, generator = _open_db()
    try:
        observed_at = datetime(2026, 8, 4, 10, 0, 0)
        db.add(
            QuickSearchPopularityDaily(
                search_date=search_date,
                origin_iata=origin,
                destination_iata=destination,
                currency="EUR",
                search_count=count,
                first_searched_at=observed_at,
                last_searched_at=observed_at,
            )
        )
        db.commit()
    finally:
        _close_db(db, generator)


def _create_watch(client, email: str, origin: str, destination: str) -> str:
    token = register_and_token(client, email=email)
    response = client.post(
        "/api/v1/watchlist",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "origin_iata": origin,
            "destination_iata": destination,
            "travel_date_local": "2026-09-03",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _snapshot(db: Session) -> CommunityTrendingSnapshot:
    snapshot = db.scalar(
        select(CommunityTrendingSnapshot).order_by(
            CommunityTrendingSnapshot.calculated_at_utc.desc(),
            CommunityTrendingSnapshot.id.desc(),
        )
    )
    assert snapshot is not None
    return snapshot


def test_notify_persists_stable_top_twenty_percent_and_seven_day_window(client) -> None:
    reporting_date = date(2026, 8, 4)
    routes = [
        ("MAD", "BCN", 20),
        ("MAD", "LIS", 15),
        ("AGP", "FCO", 10),
        ("SVQ", "BIO", 8),
        ("ALC", "PMI", 5),
        ("BIO", "LPA", 4),
    ]
    for origin, destination, count in routes:
        _seed_route(origin, destination, count, search_date=reporting_date)
    _seed_route("LPA", "TFN", 99, search_date=reporting_date - timedelta(days=7))
    _create_watch(client, "trending-persist@viru.dev", "MAD", "BCN")

    db, generator = _open_db()
    try:
        persisted = notify_trending_routes(
            db,
            today=reporting_date,
            now=datetime(2026, 8, 4, 12, 0, 0),
        )
        snapshot = _snapshot(db)
        routes_in_snapshot = list(
            db.scalars(
                select(CommunityTrendingSnapshotRoute)
                .where(CommunityTrendingSnapshotRoute.snapshot_id == snapshot.id)
                .order_by(CommunityTrendingSnapshotRoute.rank)
            )
        )
        community_columns = {
            column.name for column in CommunityTrendingSnapshot.__table__.columns
        } | {column.name for column in CommunityTrendingSnapshotRoute.__table__.columns}
    finally:
        _close_db(db, generator)

    assert persisted == 2
    assert snapshot.status == "published"
    assert snapshot.reporting_date == reporting_date
    assert snapshot.window_start_date == reporting_date - timedelta(days=6)
    assert snapshot.window_end_date == reporting_date
    assert snapshot.route_count == 2
    assert [(row.origin_iata, row.destination_iata, row.rank, row.search_count) for row in routes_in_snapshot] == [
        ("MAD", "BCN", 1, 20),
        ("MAD", "LIS", 2, 15),
    ]
    assert snapshot.expires_at_utc == datetime(2026, 8, 4, 13, 0, 0)
    assert not {"user_id", "watch_id", "email"}.intersection(community_columns)


def test_notify_publishes_empty_snapshot_to_clear_legacy_results(client) -> None:
    reporting_date = date(2026, 8, 4)
    _seed_route("MAD", "BCN", 20, search_date=reporting_date)

    db, generator = _open_db()
    try:
        assert notify_trending_routes(db, today=reporting_date, now=datetime(2026, 8, 4, 10)) == 1
        db.execute(delete(QuickSearchPopularityDaily))
        db.commit()
        assert notify_trending_routes(db, today=reporting_date, now=datetime(2026, 8, 4, 11)) == 0
        snapshots = list(
            db.scalars(
                select(CommunityTrendingSnapshot).order_by(
                    CommunityTrendingSnapshot.calculated_at_utc
                )
            )
        )
        empty_route_count = db.scalar(
            select(CommunityTrendingSnapshotRoute.id).where(
                CommunityTrendingSnapshotRoute.snapshot_id == snapshots[1].id
            )
        )
    finally:
        _close_db(db, generator)

    assert len(snapshots) == 2
    assert snapshots[0].route_count == 1
    assert snapshots[1].status == "published"
    assert snapshots[1].route_count == 0
    assert empty_route_count is None


def test_notify_rolls_back_failed_snapshot_and_preserves_previous(client, monkeypatch) -> None:
    reporting_date = date(2026, 8, 4)
    _seed_route("MAD", "BCN", 20, search_date=reporting_date)
    _create_watch(client, "trending-rollback@viru.dev", "MAD", "BCN")

    db, generator = _open_db()
    try:
        notify_trending_routes(db, today=reporting_date, now=datetime(2026, 8, 4, 10))
        previous_id = _snapshot(db).id
        original_commit = db.commit

        def failing_commit() -> None:
            raise RuntimeError("test commit failure")

        monkeypatch.setattr(db, "commit", failing_commit)
        with pytest.raises(RuntimeError, match="test commit failure"):
            notify_trending_routes(db, today=reporting_date, now=datetime(2026, 8, 4, 11))
        monkeypatch.setattr(db, "commit", original_commit)
        snapshots = list(db.scalars(select(CommunityTrendingSnapshot)))
    finally:
        _close_db(db, generator)

    assert [snapshot.id for snapshot in snapshots] == [previous_id]
    assert snapshots[0].status == "published"
    assert snapshots[0].route_count == 1
