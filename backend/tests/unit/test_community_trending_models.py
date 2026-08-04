from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.infrastructure.db.models import (
    CommunityTrendingSnapshot,
    CommunityTrendingSnapshotRoute,
)


def test_community_trending_snapshot_model_has_expected_columns_and_indexes() -> None:
    table = CommunityTrendingSnapshot.__table__

    assert table.name == "community_trending_snapshot"
    assert {
        column.name
        for column in table.columns
    } == {
        "id",
        "reporting_date",
        "window_start_date",
        "window_end_date",
        "calculated_at_utc",
        "published_at_utc",
        "expires_at_utc",
        "status",
        "route_count",
        "created_at",
    }
    assert {index.name for index in table.indexes} == {
        "ix_community_trending_snapshot_status_calculated",
        "ix_community_trending_snapshot_status_expires",
        "ix_community_trending_snapshot_reporting_date",
    }
    assert not any(
        column.name in {"user_id", "watch_id", "email"}
        for column in table.columns
    )


def test_community_trending_snapshot_route_is_directional_and_user_agnostic() -> None:
    table = CommunityTrendingSnapshotRoute.__table__

    assert table.name == "community_trending_snapshot_route"
    assert {
        column.name
        for column in table.columns
    } == {
        "id",
        "snapshot_id",
        "origin_iata",
        "destination_iata",
        "rank",
        "search_count",
        "created_at",
    }
    assert {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    } == {"uq_community_trending_snapshot_route"}
    assert {
        constraint.name
        for constraint in table.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    } == {
        "ck_community_trending_snapshot_route_rank",
        "ck_community_trending_snapshot_route_search_count",
    }
    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(foreign_keys) == 1
    assert foreign_keys[0].referred_table.name == "community_trending_snapshot"
    assert foreign_keys[0].elements[0].ondelete == "CASCADE"
    assert {
        index.name
        for index in table.indexes
    } == {
        "ix_community_trending_snapshot_route_snapshot_rank",
        "ix_community_trending_snapshot_route_snapshot_route",
    }
    assert not any(
        column.name in {"user_id", "watch_id", "email"}
        for column in table.columns
    )


def test_snapshot_relationship_orders_routes_by_rank() -> None:
    relationship = CommunityTrendingSnapshot.__mapper__.relationships["routes"]

    assert relationship.back_populates == "snapshot"
    assert relationship.cascade.delete_orphan
    assert "rank" in str(relationship.order_by)
