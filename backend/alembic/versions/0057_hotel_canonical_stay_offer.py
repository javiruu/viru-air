from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0057_hotel_canonical_stay_offer"
down_revision: Union[str, None] = "0056_hotel_saved_searches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotel_stay_offer",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("canonical_hotel_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_hotel_id", sa.String(length=120), nullable=False),
        sa.Column("fingerprint_version", sa.String(length=24), nullable=False, server_default="hotel-stay-v2"),
        sa.Column("stay_query_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("offer_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("canonical_query_json", sa.Text(), nullable=False),
        sa.Column("conditions_completeness", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("fee_semantics", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_hotel_id"], ["hotel_property.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_hotel_id",
            "stay_query_fingerprint",
            "offer_fingerprint",
            name="uq_hotel_stay_offer_identity",
        ),
    )
    op.create_index("ix_hotel_stay_offer_canonical_hotel_id", "hotel_stay_offer", ["canonical_hotel_id"])
    op.create_index("ix_hotel_stay_offer_provider", "hotel_stay_offer", ["provider"])
    op.create_index("ix_hotel_stay_offer_stay_query_fingerprint", "hotel_stay_offer", ["stay_query_fingerprint"])
    op.create_index("ix_hotel_stay_offer_offer_fingerprint", "hotel_stay_offer", ["offer_fingerprint"])
    op.create_index("ix_hotel_stay_offer_hotel_provider", "hotel_stay_offer", ["canonical_hotel_id", "provider"])

    with op.batch_alter_table("hotel_rate_snapshot") as batch_op:
        batch_op.add_column(sa.Column("stay_offer_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("observed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("stay_query_fingerprint", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("offer_fingerprint", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("snapshot_outcome", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("price_semantics", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("amount_base", sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column("amount_total", sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column("fees_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("conditions_completeness", sa.String(length=16), nullable=True))
        batch_op.create_foreign_key(
            "fk_hotel_rate_snapshot_stay_offer_id",
            "hotel_stay_offer",
            ["stay_offer_id"],
            ["id"],
        )
        batch_op.create_index("ix_hotel_rate_snapshot_stay_offer_id", ["stay_offer_id"])
        batch_op.create_index("ix_hotel_rate_snapshot_observed_at", ["observed_at"])
        batch_op.create_index("ix_hotel_rate_snapshot_stay_query_fingerprint", ["stay_query_fingerprint"])
        batch_op.create_index("ix_hotel_rate_snapshot_offer_fingerprint", ["offer_fingerprint"])

    op.create_table(
        "hotel_user_stay_watch",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("stay_offer_id", sa.String(length=36), nullable=False),
        sa.Column("legacy_tracked_offer_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stay_offer_id"], ["hotel_stay_offer.id"]),
        sa.ForeignKeyConstraint(["legacy_tracked_offer_id"], ["hotel_tracked_offer.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "stay_offer_id", name="uq_hotel_user_stay_watch_identity"),
        sa.UniqueConstraint("legacy_tracked_offer_id", name="uq_hotel_user_stay_watch_legacy"),
    )
    op.create_index("ix_hotel_user_stay_watch_user_id", "hotel_user_stay_watch", ["user_id"])
    op.create_index("ix_hotel_user_stay_watch_stay_offer_id", "hotel_user_stay_watch", ["stay_offer_id"])
    op.create_index("ix_hotel_user_stay_watch_legacy_tracked_offer_id", "hotel_user_stay_watch", ["legacy_tracked_offer_id"])
    op.create_index("ix_hotel_user_stay_watch_status", "hotel_user_stay_watch", ["status"])
    op.create_index("ix_hotel_user_stay_watch_user_status_updated", "hotel_user_stay_watch", ["user_id", "status", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_hotel_user_stay_watch_user_status_updated", table_name="hotel_user_stay_watch")
    op.drop_index("ix_hotel_user_stay_watch_status", table_name="hotel_user_stay_watch")
    op.drop_index("ix_hotel_user_stay_watch_legacy_tracked_offer_id", table_name="hotel_user_stay_watch")
    op.drop_index("ix_hotel_user_stay_watch_stay_offer_id", table_name="hotel_user_stay_watch")
    op.drop_index("ix_hotel_user_stay_watch_user_id", table_name="hotel_user_stay_watch")
    op.drop_table("hotel_user_stay_watch")

    with op.batch_alter_table("hotel_rate_snapshot") as batch_op:
        batch_op.drop_index("ix_hotel_rate_snapshot_offer_fingerprint")
        batch_op.drop_index("ix_hotel_rate_snapshot_stay_query_fingerprint")
        batch_op.drop_index("ix_hotel_rate_snapshot_observed_at")
        batch_op.drop_index("ix_hotel_rate_snapshot_stay_offer_id")
        batch_op.drop_constraint("fk_hotel_rate_snapshot_stay_offer_id", type_="foreignkey")
        batch_op.drop_column("conditions_completeness")
        batch_op.drop_column("fees_json")
        batch_op.drop_column("amount_total")
        batch_op.drop_column("amount_base")
        batch_op.drop_column("price_semantics")
        batch_op.drop_column("snapshot_outcome")
        batch_op.drop_column("offer_fingerprint")
        batch_op.drop_column("stay_query_fingerprint")
        batch_op.drop_column("observed_at")
        batch_op.drop_column("stay_offer_id")

    op.drop_index("ix_hotel_stay_offer_hotel_provider", table_name="hotel_stay_offer")
    op.drop_index("ix_hotel_stay_offer_offer_fingerprint", table_name="hotel_stay_offer")
    op.drop_index("ix_hotel_stay_offer_stay_query_fingerprint", table_name="hotel_stay_offer")
    op.drop_index("ix_hotel_stay_offer_provider", table_name="hotel_stay_offer")
    op.drop_index("ix_hotel_stay_offer_canonical_hotel_id", table_name="hotel_stay_offer")
    op.drop_table("hotel_stay_offer")
