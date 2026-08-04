from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.infrastructure.db.models import (
    CommunityTrendingSnapshot,
    CommunityTrendingSnapshotRoute,
    FlightWatch,
    User,
    UserNotificationState,
)
from app.core.time import utc_now_naive
from app.infrastructure.db.session import get_db
from app.main import app
from app.services.community_trending_notifier import build_community_trending_source_id
from tests.helpers import register_and_token


def _open_db_session():
    generator = app.dependency_overrides[get_db]()
    return next(generator), generator


def _close_db_session(generator) -> None:
    try:
        next(generator)
    except StopIteration:
        pass


def _watch(client, email: str, origin: str, destination: str) -> tuple[str, dict[str, str]]:
    token = register_and_token(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={
            "origin_iata": origin,
            "destination_iata": destination,
            "travel_date_local": "2026-09-03",
        },
    )
    assert response.status_code == 200
    return response.json()["id"], headers


def _published_snapshot(
    db,
    *,
    reporting_date: date,
    calculated_at: datetime,
    expires_at: datetime,
    routes: list[tuple[str, str, int]],
) -> str:
    snapshot = CommunityTrendingSnapshot(
        reporting_date=reporting_date,
        window_start_date=reporting_date - timedelta(days=6),
        window_end_date=reporting_date,
        calculated_at_utc=calculated_at,
        published_at_utc=calculated_at,
        expires_at_utc=expires_at,
        status="published",
        route_count=len(routes),
    )
    snapshot.routes = [
        CommunityTrendingSnapshotRoute(
            origin_iata=origin,
            destination_iata=destination,
            rank=index,
            search_count=count,
            created_at=calculated_at,
        )
        for index, (origin, destination, count) in enumerate(routes, start=1)
    ]
    db.add(snapshot)
    db.commit()
    return snapshot.id


def test_inbox_reads_persisted_snapshot_after_cache_is_cleared(client) -> None:
    watch_id, headers = _watch(client, "persistent-inbox@viru.dev", "MAD", "BCN")
    del watch_id
    calculated_at = utc_now_naive().replace(microsecond=0)
    reporting_date = calculated_at.date()
    db, generator = _open_db_session()
    try:
        snapshot_id = _published_snapshot(
            db,
            reporting_date=reporting_date,
            calculated_at=calculated_at,
            expires_at=calculated_at + timedelta(hours=1),
            routes=[("MAD", "BCN", 20)],
        )
    finally:
        _close_db_session(generator)

    inbox = client.get("/api/v1/notifications", headers=headers)
    assert inbox.status_code == 200
    item = next(item for item in inbox.json()["items"] if item["category"] == "community")
    assert item["source_type"] == "community_trending"
    assert item["source_id"] == build_community_trending_source_id(reporting_date, "MAD", "BCN")
    assert item["id"] == f"community_trending:{item['source_id']}"
    assert item["route_label"] == "MAD → BCN"
    assert snapshot_id


def test_inbox_deduplicates_multiple_watches_and_respects_route_direction(client) -> None:
    _, headers = _watch(client, "persistent-dedup@viru.dev", "MAD", "BCN")
    calculated_at = utc_now_naive().replace(microsecond=0)
    db, generator = _open_db_session()
    try:
        user_id = db.scalar(select(User.id).where(User.email == "persistent-dedup@viru.dev"))
        assert user_id is not None
        db.add(
            FlightWatch(
                user_id=user_id,
                origin_iata="MAD",
                destination_iata="BCN",
                travel_date_local=date(2026, 10, 3),
            )
        )
        _published_snapshot(
            db,
            reporting_date=calculated_at.date(),
            calculated_at=calculated_at,
            expires_at=calculated_at + timedelta(hours=1),
            routes=[("MAD", "BCN", 20), ("BCN", "MAD", 19)],
        )
    finally:
        _close_db_session(generator)

    community_items = [
        item
        for item in client.get("/api/v1/notifications", headers=headers).json()["items"]
        if item["category"] == "community"
    ]
    assert len(community_items) == 1
    assert community_items[0]["route_label"] == "MAD → BCN"


def test_expired_snapshot_is_not_listed_and_cannot_be_marked_read(client) -> None:
    _, headers = _watch(client, "persistent-expired@viru.dev", "MAD", "BCN")
    calculated_at = utc_now_naive().replace(microsecond=0)
    reporting_date = calculated_at.date()
    source_id = build_community_trending_source_id(reporting_date, "MAD", "BCN")
    db, generator = _open_db_session()
    try:
        _published_snapshot(
            db,
            reporting_date=reporting_date,
            calculated_at=calculated_at - timedelta(hours=2),
            expires_at=calculated_at - timedelta(hours=1),
            routes=[("MAD", "BCN", 20)],
        )
    finally:
        _close_db_session(generator)

    listed = client.get("/api/v1/notifications", headers=headers)
    assert listed.status_code == 200
    assert not any(item["source_id"] == source_id for item in listed.json()["items"])
    mark = client.post(
        f"/api/v1/notifications/community_trending/{source_id}/read",
        headers=headers,
    )
    assert mark.status_code == 404


def test_summary_and_read_all_include_persistent_community_items(client) -> None:
    _, headers = _watch(client, "persistent-summary@viru.dev", "MAD", "BCN")
    calculated_at = utc_now_naive().replace(microsecond=0)
    reporting_date = calculated_at.date()
    db, generator = _open_db_session()
    try:
        _published_snapshot(
            db,
            reporting_date=reporting_date,
            calculated_at=calculated_at,
            expires_at=calculated_at + timedelta(hours=1),
            routes=[("MAD", "BCN", 20)],
        )
    finally:
        _close_db_session(generator)

    listed = client.get("/api/v1/notifications", headers=headers).json()
    summary = client.get("/api/v1/notifications/summary", headers=headers).json()
    assert listed["summary"]["community"] == 1
    assert summary["community"] == 1
    assert summary["unread"] == 2

    read_all = client.post("/api/v1/notifications/read-all", headers=headers)
    assert read_all.status_code == 200
    assert read_all.json()["updated"] == 2
    assert client.get("/api/v1/notifications/summary", headers=headers).json()["unread"] == 0


def test_community_mark_read_rejects_missing_paused_and_reverse_routes(client) -> None:
    _, owner_headers = _watch(client, "persistent-owner-valid@viru.dev", "MAD", "BCN")
    _, paused_headers = _watch(client, "persistent-owner-paused@viru.dev", "MAD", "BCN")
    _, outsider_headers = _watch(client, "persistent-owner-reverse@viru.dev", "BCN", "MAD")
    calculated_at = utc_now_naive().replace(microsecond=0)
    reporting_date = calculated_at.date()
    source_id = build_community_trending_source_id(reporting_date, "MAD", "BCN")
    db, generator = _open_db_session()
    try:
        paused_user_id = db.scalar(
            select(User.id).where(User.email == "persistent-owner-paused@viru.dev")
        )
        assert paused_user_id is not None
        paused_watch = db.scalar(
            select(FlightWatch).where(FlightWatch.user_id == paused_user_id)
        )
        assert paused_watch is not None
        paused_watch.status = "paused"
        _published_snapshot(
            db,
            reporting_date=reporting_date,
            calculated_at=calculated_at,
            expires_at=calculated_at + timedelta(hours=1),
            routes=[("MAD", "BCN", 20)],
        )
    finally:
        _close_db_session(generator)

    for headers in (paused_headers, outsider_headers):
        response = client.post(
            f"/api/v1/notifications/community_trending/{source_id}/read",
            headers=headers,
        )
        assert response.status_code == 404

    valid = client.post(
        f"/api/v1/notifications/community_trending/{source_id}/read",
        headers=owner_headers,
    )
    assert valid.status_code == 200


def test_community_mark_read_is_owned_per_user_and_idempotent(client) -> None:
    _, first_headers = _watch(client, "persistent-owner-a@viru.dev", "MAD", "BCN")
    _, second_headers = _watch(client, "persistent-owner-b@viru.dev", "MAD", "BCN")
    calculated_at = utc_now_naive().replace(microsecond=0)
    reporting_date = calculated_at.date()
    source_id = build_community_trending_source_id(reporting_date, "MAD", "BCN")
    db, generator = _open_db_session()
    try:
        _published_snapshot(
            db,
            reporting_date=reporting_date,
            calculated_at=calculated_at,
            expires_at=calculated_at + timedelta(hours=1),
            routes=[("MAD", "BCN", 20)],
        )
    finally:
        _close_db_session(generator)

    first_mark = client.post(
        f"/api/v1/notifications/community_trending/{source_id}/read",
        headers=first_headers,
    )
    assert first_mark.status_code == 200
    second_mark = client.post(
        f"/api/v1/notifications/community_trending/{source_id}/read",
        headers=second_headers,
    )
    assert second_mark.status_code == 200
    repeated = client.post(
        f"/api/v1/notifications/community_trending/{source_id}/read",
        headers=first_headers,
    )
    assert repeated.status_code == 200

    db, generator = _open_db_session()
    try:
        states = db.scalars(
            select(UserNotificationState).where(
                UserNotificationState.source_type == "community_trending",
                UserNotificationState.source_id == source_id,
            )
        ).all()
    finally:
        _close_db_session(generator)
    assert len(states) == 2
    assert len({state.user_id for state in states}) == 2
