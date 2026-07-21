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


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _has_unique_columns(table_name: str, columns: set[str]) -> bool:
    return any(
        set(constraint["column_names"]) == columns
        for constraint in _inspector().get_unique_constraints(table_name)
    )


def _ensure_index(
    name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if name not in _index_names(table_name):
        op.create_index(name, table_name, columns, unique=unique)


def _require_columns(table_name: str, required: set[str]) -> None:
    missing = required - _column_names(table_name)
    if missing:
        formatted = ", ".join(sorted(missing))
        raise RuntimeError(f"Cannot reconcile {table_name}; missing columns: {formatted}")


def upgrade() -> None:
    if not _table_exists("watch_tracked_flight_leg"):
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
            sa.UniqueConstraint(
                "watch_id", "sequence", name="uq_watch_tracked_flight_leg_sequence"
            ),
        )
    elif "departure_date_local" not in _column_names("watch_tracked_flight_leg"):
        op.add_column(
            "watch_tracked_flight_leg",
            sa.Column("departure_date_local", sa.Date(), nullable=True),
        )
    _require_columns(
        "watch_tracked_flight_leg",
        set(
            "id watch_id sequence flight_instance_fingerprint carrier_code flight_number "
            "origin_iata destination_iata departure_date_local scheduled_departure_at "
            "scheduled_arrival_at identity_source created_at updated_at".split()
        ),
    )
    _ensure_index(
        "ix_watch_tracked_flight_leg_watch_id",
        "watch_tracked_flight_leg",
        ["watch_id"],
    )
    _ensure_index(
        "ix_watch_tracked_flight_leg_instance",
        "watch_tracked_flight_leg",
        ["flight_instance_fingerprint"],
    )

    if not _table_exists("flight_operational_snapshot"):
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
    _require_columns(
        "flight_operational_snapshot",
        set(
            "id flight_instance_fingerprint provider provider_flight_id flight_number callsign "
            "icao24 status status_raw observed_at expires_at scheduled_departure_at "
            "estimated_departure_at actual_departure_at scheduled_arrival_at "
            "estimated_arrival_at actual_arrival_at departure_terminal departure_gate "
            "arrival_terminal arrival_gate departure_delay_minutes arrival_delay_minutes "
            "latitude longitude altitude_m speed_mps heading_deg on_ground registration "
            "aircraft_iata aircraft_icao data_quality created_at".split()
        ),
    )
    if not _has_unique_columns(
        "flight_operational_snapshot",
        {"flight_instance_fingerprint", "provider", "observed_at"},
    ):
        with op.batch_alter_table("flight_operational_snapshot") as batch_op:
            batch_op.create_unique_constraint(
                "uq_flight_operational_snapshot_observation",
                ["flight_instance_fingerprint", "provider", "observed_at"],
            )
    _ensure_index(
        "ix_flight_operational_snapshot_instance_observed",
        "flight_operational_snapshot",
        ["flight_instance_fingerprint", "observed_at"],
    )
    _ensure_index(
        "ix_flight_operational_snapshot_expires",
        "flight_operational_snapshot",
        ["expires_at"],
    )
    _ensure_index(
        "ix_flight_operational_snapshot_provider_flight",
        "flight_operational_snapshot",
        ["provider", "provider_flight_id"],
    )
    _ensure_index(
        "ix_flight_operational_snapshot_observed_at",
        "flight_operational_snapshot",
        ["observed_at"],
    )

    if not _table_exists("flight_operational_refresh_lock"):
        op.create_table(
            "flight_operational_refresh_lock",
            sa.Column("flight_instance_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("lock_token", sa.String(length=64), nullable=False),
            sa.Column("acquired_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("outcome", sa.String(length=24), nullable=True),
            sa.PrimaryKeyConstraint("flight_instance_fingerprint"),
        )
    elif "outcome" not in _column_names("flight_operational_refresh_lock"):
        op.add_column(
            "flight_operational_refresh_lock",
            sa.Column("outcome", sa.String(length=24), nullable=True),
        )
    _require_columns(
        "flight_operational_refresh_lock",
        {"flight_instance_fingerprint", "lock_token", "acquired_at", "expires_at", "outcome"},
    )
    for legacy_index in (
        "ix_flight_operational_refresh_lock_lock_token",
        "ix_flight_operational_refresh_lock_expires_at",
    ):
        if legacy_index in _index_names("flight_operational_refresh_lock"):
            op.drop_index(legacy_index, table_name="flight_operational_refresh_lock")
    _ensure_index(
        "ix_flight_operational_refresh_lock_token",
        "flight_operational_refresh_lock",
        ["lock_token"],
        unique=True,
    )
    _ensure_index(
        "ix_flight_operational_refresh_lock_expires",
        "flight_operational_refresh_lock",
        ["expires_at"],
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
