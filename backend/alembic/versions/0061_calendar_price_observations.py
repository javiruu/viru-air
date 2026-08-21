from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0061_calendar_price_observations"
down_revision: Union[str, None] = "0060_revalidation_job_active_target"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_price_observation",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("reference_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("route_signature", sa.String(length=255), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("leg", sa.String(length=16), nullable=False, server_default="outbound"),
        sa.Column("adults", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cabin", sa.String(length=32), nullable=False, server_default="economy"),
        sa.Column("aggregation_mode", sa.String(length=16), nullable=False, server_default="min"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="calendar-aggregate"),
        sa.Column("raw_price_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("raw_currency", sa.String(length=3), nullable=True),
        sa.Column("normalized_price_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("freshness_status", sa.String(length=32), nullable=False, server_default="fresh"),
        sa.Column("coverage_status", sa.String(length=32), nullable=False, server_default="partial"),
        sa.Column("validation_status", sa.String(length=32), nullable=False, server_default="observed"),
        sa.Column("source_kind", sa.String(length=32), nullable=False, server_default="calendar_hint"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "query_fingerprint",
            "route_signature",
            "provider",
            "observed_at",
            name="uq_calendar_price_observation_sample",
        ),
    )
    op.create_index(
        "ix_calendar_price_observation_reference",
        "calendar_price_observation",
        ["reference_fingerprint", "observed_at"],
    )
    op.create_index(
        "ix_calendar_price_observation_day",
        "calendar_price_observation",
        ["query_fingerprint", "travel_date", "observed_at"],
    )
    op.create_index(
        "ix_calendar_price_observation_expires",
        "calendar_price_observation",
        ["expires_at"],
    )
    with op.batch_alter_table("user_preference") as batch_op:
        batch_op.alter_column(
            "calendar_hint_bucket_mode_default",
            existing_type=sa.String(length=24),
            server_default="contextual",
        )
    op.execute(
        "UPDATE user_preference "
        "SET calendar_hint_bucket_mode_default = 'contextual' "
        "WHERE calendar_hint_bucket_mode_default = 'monthly_terciles'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE user_preference "
        "SET calendar_hint_bucket_mode_default = 'monthly_terciles' "
        "WHERE calendar_hint_bucket_mode_default = 'contextual'"
    )
    with op.batch_alter_table("user_preference") as batch_op:
        batch_op.alter_column(
            "calendar_hint_bucket_mode_default",
            existing_type=sa.String(length=24),
            server_default="monthly_terciles",
        )
    op.drop_index("ix_calendar_price_observation_expires", table_name="calendar_price_observation")
    op.drop_index("ix_calendar_price_observation_day", table_name="calendar_price_observation")
    op.drop_index("ix_calendar_price_observation_reference", table_name="calendar_price_observation")
    op.drop_table("calendar_price_observation")
