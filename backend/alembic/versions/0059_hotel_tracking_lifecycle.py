from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0059_hotel_tracking_lifecycle"
down_revision: Union[str, None] = "0058_hotel_tracked_offer_offer_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hotel_tracked_offer") as batch_op:
        batch_op.add_column(sa.Column("lifecycle_state", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("lifecycle_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("lifecycle_changed_at", sa.DateTime(), nullable=True))

    tracked_offer = sa.table(
        "hotel_tracked_offer",
        sa.column("is_active", sa.Boolean()),
        sa.column("lifecycle_state", sa.String(length=24)),
        sa.column("lifecycle_version", sa.Integer()),
    )
    op.execute(
        tracked_offer.update().values(
            lifecycle_state=sa.case(
                (tracked_offer.c.is_active.is_(True), "active"),
                else_="paused",
            ),
            lifecycle_version=1,
        )
    )
    with op.batch_alter_table("hotel_tracked_offer") as batch_op:
        batch_op.alter_column(
            "lifecycle_state",
            existing_type=sa.String(length=24),
            nullable=False,
            server_default="active",
        )
        batch_op.alter_column(
            "lifecycle_version",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="1",
        )
        batch_op.create_index("ix_hotel_tracked_offer_lifecycle_state", ["lifecycle_state"])

    op.create_table(
        "hotel_tracked_offer_lifecycle_event",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tracked_offer_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("from_state", sa.String(length=24), nullable=False),
        sa.Column("to_state", sa.String(length=24), nullable=False),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tracked_offer_id"], ["hotel_tracked_offer.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracked_offer_id", "state_version", name="uq_hotel_tracking_lifecycle_version"),
    )
    op.create_index(
        "ix_hotel_tracking_lifecycle_offer_created",
        "hotel_tracked_offer_lifecycle_event",
        ["tracked_offer_id", "created_at"],
    )
    op.create_index(
        "ix_hotel_tracking_lifecycle_user_created",
        "hotel_tracked_offer_lifecycle_event",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    lifecycle_events = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM hotel_tracked_offer_lifecycle_event")
    ).scalar_one()
    if lifecycle_events:
        raise RuntimeError("hotel_tracking_0059_downgrade_requires_lifecycle_event_retention")

    op.drop_index("ix_hotel_tracking_lifecycle_user_created", table_name="hotel_tracked_offer_lifecycle_event")
    op.drop_index("ix_hotel_tracking_lifecycle_offer_created", table_name="hotel_tracked_offer_lifecycle_event")
    op.drop_table("hotel_tracked_offer_lifecycle_event")
    with op.batch_alter_table("hotel_tracked_offer") as batch_op:
        batch_op.drop_index("ix_hotel_tracked_offer_lifecycle_state")
        batch_op.drop_column("lifecycle_changed_at")
        batch_op.drop_column("lifecycle_version")
        batch_op.drop_column("lifecycle_state")
