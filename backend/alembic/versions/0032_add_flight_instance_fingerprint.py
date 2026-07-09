"""add flight instance fingerprint

Revision ID: 0032_add_flight_instance_fingerprint
Revises: 0031_add_user_notification_state
Create Date: 2026-07-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0032_add_flight_instance_fingerprint"
down_revision: str | None = "0031_add_user_notification_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {str(index["name"]) for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "flight_offer_cache_entry" not in _table_names(inspector):
        return

    columns = _column_names(inspector, "flight_offer_cache_entry")
    with op.batch_alter_table("flight_offer_cache_entry") as batch_op:
        if "flight_instance_fingerprint" not in columns:
            batch_op.add_column(sa.Column("flight_instance_fingerprint", sa.String(length=64), nullable=True))
        if "carrier_code" not in columns:
            batch_op.add_column(sa.Column("carrier_code", sa.String(length=16), nullable=True))
        if "departure_time_local" not in columns:
            batch_op.add_column(sa.Column("departure_time_local", sa.String(length=16), nullable=True))
        if "arrival_time_local" not in columns:
            batch_op.add_column(sa.Column("arrival_time_local", sa.String(length=16), nullable=True))

    inspector = sa.inspect(op.get_bind())
    indexes = _index_names(inspector, "flight_offer_cache_entry")
    if "ix_flight_offer_cache_instance" not in indexes:
        op.create_index(
            "ix_flight_offer_cache_instance",
            "flight_offer_cache_entry",
            ["flight_instance_fingerprint"],
            unique=False,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "flight_offer_cache_entry" not in _table_names(inspector):
        return

    indexes = _index_names(inspector, "flight_offer_cache_entry")
    if "ix_flight_offer_cache_instance" in indexes:
        op.drop_index("ix_flight_offer_cache_instance", table_name="flight_offer_cache_entry")

    columns = _column_names(sa.inspect(op.get_bind()), "flight_offer_cache_entry")
    with op.batch_alter_table("flight_offer_cache_entry") as batch_op:
        if "arrival_time_local" in columns:
            batch_op.drop_column("arrival_time_local")
        if "departure_time_local" in columns:
            batch_op.drop_column("departure_time_local")
        if "carrier_code" in columns:
            batch_op.drop_column("carrier_code")
        if "flight_instance_fingerprint" in columns:
            batch_op.drop_column("flight_instance_fingerprint")
