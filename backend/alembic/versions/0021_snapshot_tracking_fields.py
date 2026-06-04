"""add snapshot tracking fields — tracked_offer_id, provider_run_id, availability_status, deep_link

Revision ID: 0021_snapshot_tracking_fields
Revises: 0020_hotel_tracked_offer
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0021_snapshot_tracking_fields"
down_revision = "0020_hotel_tracked_offer"
branch_labels = None
depends_on = None


def _table_names(conn) -> set[str]:
    inspector = sa.inspect(conn)
    return set(inspector.get_table_names())


def _column_names(conn, table_name: str) -> set[str]:
    insp = sa.inspect(conn)
    cols = insp.get_columns(table_name)
    return {col["name"] for col in cols}


def _index_names(conn, table_name: str) -> set[str]:
    insp = sa.inspect(conn)
    return {idx["name"] for idx in insp.get_indexes(table_name)}


def upgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "hotel_rate_snapshot" not in tables:
        return

    columns = _column_names(conn, "hotel_rate_snapshot")

    with op.batch_alter_table("hotel_rate_snapshot") as batch_op:
        if "tracked_offer_id" not in columns:
            batch_op.add_column(sa.Column("tracked_offer_id", sa.String(length=36), nullable=True))
            batch_op.create_foreign_key(
                "fk_hotel_rate_snapshot_tracked_offer",
                "hotel_tracked_offer",
                ["tracked_offer_id"],
                ["id"],
            )
        if "provider_run_id" not in columns:
            batch_op.add_column(sa.Column("provider_run_id", sa.String(length=36), nullable=True))
            batch_op.create_foreign_key(
                "fk_hotel_rate_snapshot_provider_run",
                "hotel_provider_run",
                ["provider_run_id"],
                ["id"],
            )
        if "availability_status" not in columns:
            batch_op.add_column(
                sa.Column("availability_status", sa.String(length=20), nullable=False, server_default="available")
            )
        if "deep_link" not in columns:
            batch_op.add_column(sa.Column("deep_link", sa.String(length=500), nullable=True))

    indexes = _index_names(conn, "hotel_rate_snapshot")
    if "ix_hotel_rate_snapshot_tracked_offer_id" not in indexes:
        op.create_index("ix_hotel_rate_snapshot_tracked_offer_id", "hotel_rate_snapshot", ["tracked_offer_id"])
    if "ix_hotel_rate_snapshot_provider_run_id" not in indexes:
        op.create_index("ix_hotel_rate_snapshot_provider_run_id", "hotel_rate_snapshot", ["provider_run_id"])


def downgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "hotel_rate_snapshot" not in tables:
        return

    columns = _column_names(conn, "hotel_rate_snapshot")
    indexes = _index_names(conn, "hotel_rate_snapshot")

    if "ix_hotel_rate_snapshot_provider_run_id" in indexes:
        op.drop_index("ix_hotel_rate_snapshot_provider_run_id", table_name="hotel_rate_snapshot")
    if "ix_hotel_rate_snapshot_tracked_offer_id" in indexes:
        op.drop_index("ix_hotel_rate_snapshot_tracked_offer_id", table_name="hotel_rate_snapshot")

    with op.batch_alter_table("hotel_rate_snapshot") as batch_op:
        if "deep_link" in columns:
            batch_op.drop_column("deep_link")
        if "availability_status" in columns:
            batch_op.drop_column("availability_status")
        if "provider_run_id" in columns:
            batch_op.drop_constraint("fk_hotel_rate_snapshot_provider_run", type_="foreignkey")
            batch_op.drop_column("provider_run_id")
        if "tracked_offer_id" in columns:
            batch_op.drop_constraint("fk_hotel_rate_snapshot_tracked_offer", type_="foreignkey")
            batch_op.drop_column("tracked_offer_id")
