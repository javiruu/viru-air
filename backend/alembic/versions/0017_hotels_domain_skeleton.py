"""hotels domain skeleton tables

Revision ID: 0017_hotels_domain_skeleton
Revises: 0016_remove_is_paused
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0017_hotels_domain_skeleton"
down_revision = "0016_remove_is_paused"
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

    if "hotel_property" not in tables:
        op.create_table(
            "hotel_property",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("canonical_name", sa.String(length=200), nullable=False),
            sa.Column("normalized_name", sa.String(length=200), nullable=False),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=100), nullable=False),
            sa.Column("country_code", sa.String(length=2), nullable=False),
            sa.Column("latitude", sa.Numeric(10, 6), nullable=True),
            sa.Column("longitude", sa.Numeric(10, 6), nullable=True),
            sa.Column("stars", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    if "hotel_provider_alias" not in tables:
        op.create_table(
            "hotel_provider_alias",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), sa.ForeignKey("hotel_property.id"), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("provider_hotel_id", sa.String(length=120), nullable=False),
            sa.Column("raw_name", sa.String(length=255), nullable=True),
            sa.Column("raw_address", sa.String(length=255), nullable=True),
            sa.Column("raw_payload", sa.Text(), nullable=True),
            sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
            sa.UniqueConstraint("provider", "provider_hotel_id", name="uq_hotel_provider_alias_provider_hotel_id"),
        )
    if "hotel_rate_snapshot" not in tables:
        op.create_table(
            "hotel_rate_snapshot",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("hotel_id", sa.String(length=36), sa.ForeignKey("hotel_property.id"), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("check_in", sa.Date(), nullable=False),
            sa.Column("check_out", sa.Date(), nullable=False),
            sa.Column("guests", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("room_label", sa.String(length=160), nullable=True),
            sa.Column("meal_plan", sa.String(length=80), nullable=True),
            sa.Column("cancellation_policy", sa.String(length=120), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
        )
    if "hotel_watchlist_item" not in tables:
        op.create_table(
            "hotel_watchlist_item",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("hotel_id", sa.String(length=36), sa.ForeignKey("hotel_property.id"), nullable=False),
            sa.Column("label", sa.String(length=80), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "hotel_id", name="uq_hotel_watchlist_item_user_hotel"),
        )
    if "hotel_comp_set" not in tables:
        op.create_table(
            "hotel_comp_set",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("anchor_hotel_id", sa.String(length=36), sa.ForeignKey("hotel_property.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "hotel_comp_set_member" not in tables:
        op.create_table(
            "hotel_comp_set_member",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("comp_set_id", sa.String(length=36), sa.ForeignKey("hotel_comp_set.id"), nullable=False),
            sa.Column("hotel_id", sa.String(length=36), sa.ForeignKey("hotel_property.id"), nullable=False),
            sa.UniqueConstraint("comp_set_id", "hotel_id", name="uq_hotel_comp_set_member_comp_hotel"),
        )
    if "hotel_alert_rule" not in tables:
        op.create_table(
            "hotel_alert_rule",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("hotel_id", sa.String(length=36), sa.ForeignKey("hotel_property.id"), nullable=False),
            sa.Column("rule_type", sa.String(length=40), nullable=False),
            sa.Column("threshold_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("threshold_percent", sa.Numeric(5, 2), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    # Idempotent index creation per table.
    indexes = _index_names(conn, "hotel_property")
    if "ix_hotel_property_normalized_name" not in indexes:
        op.create_index("ix_hotel_property_normalized_name", "hotel_property", ["normalized_name"])
    if "ix_hotel_property_city" not in indexes:
        op.create_index("ix_hotel_property_city", "hotel_property", ["city"])
    if "ix_hotel_property_country_code" not in indexes:
        op.create_index("ix_hotel_property_country_code", "hotel_property", ["country_code"])

    indexes = _index_names(conn, "hotel_provider_alias")
    if "ix_hotel_provider_alias_hotel_id" not in indexes:
        op.create_index("ix_hotel_provider_alias_hotel_id", "hotel_provider_alias", ["hotel_id"])
    if "ix_hotel_provider_alias_provider" not in indexes:
        op.create_index("ix_hotel_provider_alias_provider", "hotel_provider_alias", ["provider"])

    indexes = _index_names(conn, "hotel_rate_snapshot")
    if "ix_hotel_rate_snapshot_hotel_id" not in indexes:
        op.create_index("ix_hotel_rate_snapshot_hotel_id", "hotel_rate_snapshot", ["hotel_id"])
    if "ix_hotel_rate_snapshot_provider" not in indexes:
        op.create_index("ix_hotel_rate_snapshot_provider", "hotel_rate_snapshot", ["provider"])
    if "ix_hotel_rate_snapshot_check_in" not in indexes:
        op.create_index("ix_hotel_rate_snapshot_check_in", "hotel_rate_snapshot", ["check_in"])
    if "ix_hotel_rate_snapshot_check_out" not in indexes:
        op.create_index("ix_hotel_rate_snapshot_check_out", "hotel_rate_snapshot", ["check_out"])
    if "ix_hotel_rate_snapshot_collected_at" not in indexes:
        op.create_index("ix_hotel_rate_snapshot_collected_at", "hotel_rate_snapshot", ["collected_at"])

    indexes = _index_names(conn, "hotel_watchlist_item")
    if "ix_hotel_watchlist_item_user_id" not in indexes:
        op.create_index("ix_hotel_watchlist_item_user_id", "hotel_watchlist_item", ["user_id"])
    if "ix_hotel_watchlist_item_hotel_id" not in indexes:
        op.create_index("ix_hotel_watchlist_item_hotel_id", "hotel_watchlist_item", ["hotel_id"])

    indexes = _index_names(conn, "hotel_comp_set")
    if "ix_hotel_comp_set_user_id" not in indexes:
        op.create_index("ix_hotel_comp_set_user_id", "hotel_comp_set", ["user_id"])
    if "ix_hotel_comp_set_anchor_hotel_id" not in indexes:
        op.create_index("ix_hotel_comp_set_anchor_hotel_id", "hotel_comp_set", ["anchor_hotel_id"])

    indexes = _index_names(conn, "hotel_comp_set_member")
    if "ix_hotel_comp_set_member_comp_set_id" not in indexes:
        op.create_index("ix_hotel_comp_set_member_comp_set_id", "hotel_comp_set_member", ["comp_set_id"])
    if "ix_hotel_comp_set_member_hotel_id" not in indexes:
        op.create_index("ix_hotel_comp_set_member_hotel_id", "hotel_comp_set_member", ["hotel_id"])

    indexes = _index_names(conn, "hotel_alert_rule")
    if "ix_hotel_alert_rule_user_id" not in indexes:
        op.create_index("ix_hotel_alert_rule_user_id", "hotel_alert_rule", ["user_id"])
    if "ix_hotel_alert_rule_hotel_id" not in indexes:
        op.create_index("ix_hotel_alert_rule_hotel_id", "hotel_alert_rule", ["hotel_id"])


def downgrade() -> None:
    conn = op.get_bind()
    tables = _table_names(conn)

    if "hotel_alert_rule" in tables:
        indexes = _index_names(conn, "hotel_alert_rule")
        if "ix_hotel_alert_rule_hotel_id" in indexes:
            op.drop_index("ix_hotel_alert_rule_hotel_id", table_name="hotel_alert_rule")
        if "ix_hotel_alert_rule_user_id" in indexes:
            op.drop_index("ix_hotel_alert_rule_user_id", table_name="hotel_alert_rule")
        op.drop_table("hotel_alert_rule")

    if "hotel_comp_set_member" in tables:
        indexes = _index_names(conn, "hotel_comp_set_member")
        if "ix_hotel_comp_set_member_hotel_id" in indexes:
            op.drop_index("ix_hotel_comp_set_member_hotel_id", table_name="hotel_comp_set_member")
        if "ix_hotel_comp_set_member_comp_set_id" in indexes:
            op.drop_index("ix_hotel_comp_set_member_comp_set_id", table_name="hotel_comp_set_member")
        op.drop_table("hotel_comp_set_member")

    if "hotel_comp_set" in tables:
        indexes = _index_names(conn, "hotel_comp_set")
        if "ix_hotel_comp_set_anchor_hotel_id" in indexes:
            op.drop_index("ix_hotel_comp_set_anchor_hotel_id", table_name="hotel_comp_set")
        if "ix_hotel_comp_set_user_id" in indexes:
            op.drop_index("ix_hotel_comp_set_user_id", table_name="hotel_comp_set")
        op.drop_table("hotel_comp_set")

    if "hotel_watchlist_item" in tables:
        indexes = _index_names(conn, "hotel_watchlist_item")
        if "ix_hotel_watchlist_item_hotel_id" in indexes:
            op.drop_index("ix_hotel_watchlist_item_hotel_id", table_name="hotel_watchlist_item")
        if "ix_hotel_watchlist_item_user_id" in indexes:
            op.drop_index("ix_hotel_watchlist_item_user_id", table_name="hotel_watchlist_item")
        op.drop_table("hotel_watchlist_item")

    if "hotel_rate_snapshot" in tables:
        indexes = _index_names(conn, "hotel_rate_snapshot")
        if "ix_hotel_rate_snapshot_collected_at" in indexes:
            op.drop_index("ix_hotel_rate_snapshot_collected_at", table_name="hotel_rate_snapshot")
        if "ix_hotel_rate_snapshot_check_out" in indexes:
            op.drop_index("ix_hotel_rate_snapshot_check_out", table_name="hotel_rate_snapshot")
        if "ix_hotel_rate_snapshot_check_in" in indexes:
            op.drop_index("ix_hotel_rate_snapshot_check_in", table_name="hotel_rate_snapshot")
        if "ix_hotel_rate_snapshot_provider" in indexes:
            op.drop_index("ix_hotel_rate_snapshot_provider", table_name="hotel_rate_snapshot")
        if "ix_hotel_rate_snapshot_hotel_id" in indexes:
            op.drop_index("ix_hotel_rate_snapshot_hotel_id", table_name="hotel_rate_snapshot")
        op.drop_table("hotel_rate_snapshot")

    if "hotel_provider_alias" in tables:
        indexes = _index_names(conn, "hotel_provider_alias")
        if "ix_hotel_provider_alias_provider" in indexes:
            op.drop_index("ix_hotel_provider_alias_provider", table_name="hotel_provider_alias")
        if "ix_hotel_provider_alias_hotel_id" in indexes:
            op.drop_index("ix_hotel_provider_alias_hotel_id", table_name="hotel_provider_alias")
        op.drop_table("hotel_provider_alias")

    if "hotel_property" in tables:
        indexes = _index_names(conn, "hotel_property")
        if "ix_hotel_property_country_code" in indexes:
            op.drop_index("ix_hotel_property_country_code", table_name="hotel_property")
        if "ix_hotel_property_city" in indexes:
            op.drop_index("ix_hotel_property_city", table_name="hotel_property")
        if "ix_hotel_property_normalized_name" in indexes:
            op.drop_index("ix_hotel_property_normalized_name", table_name="hotel_property")
        op.drop_table("hotel_property")
