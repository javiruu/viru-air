"""add live operational flight tracking

Revision ID: 0035_add_live_flight_tracking
Revises: 0034_add_quick_search_popularity_counter
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0035_add_live_flight_tracking"
down_revision: str | None = "0034_add_quick_search_popularity_counter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watch_tracked_flight_leg",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("watch_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("flight_instance_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("carrier_code", sa.String(length=16), nullable=True),
        sa.Column("flight_number", sa.String(length=32), nullable=True),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("departure_date_local", sa.Date(), nullable=True),
        sa.Column("scheduled_departure_at", sa.DateTime(), nullable=True),
        sa.Column("scheduled_arrival_at", sa.DateTime(), nullable=True),
        sa.Column("identity_source", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["watch_id"], ["flight_watch.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("watch_id", "sequence", name="uq_watch_tracked_flight_leg_sequence"),
    )
    op.create_index(
        "ix_watch_tracked_flight_leg_watch_id",
        "watch_tracked_flight_leg",
        ["watch_id"],
        unique=False,
    )
    op.create_index(
        "ix_watch_tracked_flight_leg_instance",
        "watch_tracked_flight_leg",
        ["flight_instance_fingerprint"],
        unique=False,
    )

    op.create_table(
        "flight_operational_snapshot",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("flight_instance_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_flight_id", sa.String(length=80), nullable=True),
        sa.Column("flight_number", sa.String(length=32), nullable=True),
        sa.Column("callsign", sa.String(length=32), nullable=True),
        sa.Column("icao24", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("status_raw", sa.String(length=64), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("scheduled_departure_at", sa.DateTime(), nullable=True),
        sa.Column("estimated_departure_at", sa.DateTime(), nullable=True),
        sa.Column("actual_departure_at", sa.DateTime(), nullable=True),
        sa.Column("scheduled_arrival_at", sa.DateTime(), nullable=True),
        sa.Column("estimated_arrival_at", sa.DateTime(), nullable=True),
        sa.Column("actual_arrival_at", sa.DateTime(), nullable=True),
        sa.Column("departure_terminal", sa.String(length=32), nullable=True),
        sa.Column("departure_gate", sa.String(length=32), nullable=True),
        sa.Column("arrival_terminal", sa.String(length=32), nullable=True),
        sa.Column("arrival_gate", sa.String(length=32), nullable=True),
        sa.Column("departure_delay_minutes", sa.Integer(), nullable=True),
        sa.Column("arrival_delay_minutes", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("altitude_m", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("speed_mps", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("heading_deg", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("on_ground", sa.Boolean(), nullable=True),
        sa.Column("registration", sa.String(length=32), nullable=True),
        sa.Column("aircraft_iata", sa.String(length=16), nullable=True),
        sa.Column("aircraft_icao", sa.String(length=16), nullable=True),
        sa.Column("data_quality", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "flight_instance_fingerprint",
            "provider",
            "observed_at",
            name="uq_flight_operational_snapshot_observation",
        ),
    )
    op.create_index(
        "ix_flight_operational_snapshot_instance_observed",
        "flight_operational_snapshot",
        ["flight_instance_fingerprint", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_flight_operational_snapshot_expires",
        "flight_operational_snapshot",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_flight_operational_snapshot_provider_flight",
        "flight_operational_snapshot",
        ["provider", "provider_flight_id"],
        unique=False,
    )
    op.create_index(
        "ix_flight_operational_snapshot_observed_at",
        "flight_operational_snapshot",
        ["observed_at"],
        unique=False,
    )

    op.create_table(
        "flight_operational_refresh_lock",
        sa.Column("flight_instance_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("lock_token", sa.String(length=64), nullable=False),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=True),
        sa.PrimaryKeyConstraint("flight_instance_fingerprint"),
    )
    op.create_index(
        "ix_flight_operational_refresh_lock_token",
        "flight_operational_refresh_lock",
        ["lock_token"],
        unique=True,
    )
    op.create_index(
        "ix_flight_operational_refresh_lock_expires",
        "flight_operational_refresh_lock",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_flight_operational_refresh_lock_expires",
        table_name="flight_operational_refresh_lock",
    )
    op.drop_index(
        "ix_flight_operational_refresh_lock_token",
        table_name="flight_operational_refresh_lock",
    )
    op.drop_table("flight_operational_refresh_lock")
    op.drop_index(
        "ix_flight_operational_snapshot_observed_at",
        table_name="flight_operational_snapshot",
    )
    op.drop_index(
        "ix_flight_operational_snapshot_provider_flight",
        table_name="flight_operational_snapshot",
    )
    op.drop_index(
        "ix_flight_operational_snapshot_expires",
        table_name="flight_operational_snapshot",
    )
    op.drop_index(
        "ix_flight_operational_snapshot_instance_observed",
        table_name="flight_operational_snapshot",
    )
    op.drop_table("flight_operational_snapshot")
    op.drop_index(
        "ix_watch_tracked_flight_leg_instance",
        table_name="watch_tracked_flight_leg",
    )
    op.drop_index(
        "ix_watch_tracked_flight_leg_watch_id",
        table_name="watch_tracked_flight_leg",
    )
    op.drop_table("watch_tracked_flight_leg")
