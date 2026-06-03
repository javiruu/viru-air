"""hotel tracked offer table

Revision ID: 0020_hotel_tracked_offer
Revises: 0019_hotels_normalized_city
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_hotel_tracked_offer"
down_revision = "0019_hotels_normalized_city"
branch_labels = None
depends_on = None


def _table_names(conn) -> set[str]:
    inspector = sa.inspect(conn)
    return set(inspector.get_table_names())


def _index_names(conn, table_name: str) -> set[str]:
    insp = sa.inspect(conn)
    return {idx["name"] for idx in insp.get_indexes(table_name)}


def upgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "hotel_tracked_offer" not in tables:
        op.create_table(
            "hotel_tracked_offer",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("hotel_id", sa.String(length=36), sa.ForeignKey("hotel_property.id"), nullable=False),
            sa.Column("area_label", sa.String(length=200), nullable=True),
            sa.Column("origin_query", sa.String(length=200), nullable=True),
            sa.Column("latitude", sa.Numeric(10, 6), nullable=True),
            sa.Column("longitude", sa.Numeric(10, 6), nullable=True),
            sa.Column("radius_km", sa.Integer(), nullable=True),
            sa.Column("check_in", sa.Date(), nullable=True),
            sa.Column("check_out", sa.Date(), nullable=True),
            sa.Column("guests", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("room_label", sa.String(length=160), nullable=True),
            sa.Column("meal_plan", sa.String(length=80), nullable=True),
            sa.Column("cancellation_policy", sa.String(length=120), nullable=True),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("initial_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("current_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("target_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    indexes = _index_names(conn, "hotel_tracked_offer")
    if "ix_hotel_tracked_offer_user_id" not in indexes:
        op.create_index("ix_hotel_tracked_offer_user_id", "hotel_tracked_offer", ["user_id"])
    if "ix_hotel_tracked_offer_hotel_id" not in indexes:
        op.create_index("ix_hotel_tracked_offer_hotel_id", "hotel_tracked_offer", ["hotel_id"])


def downgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "hotel_tracked_offer" in tables:
        indexes = _index_names(conn, "hotel_tracked_offer")
        if "ix_hotel_tracked_offer_hotel_id" in indexes:
            op.drop_index("ix_hotel_tracked_offer_hotel_id", table_name="hotel_tracked_offer")
        if "ix_hotel_tracked_offer_user_id" in indexes:
            op.drop_index("ix_hotel_tracked_offer_user_id", table_name="hotel_tracked_offer")
        op.drop_table("hotel_tracked_offer")
