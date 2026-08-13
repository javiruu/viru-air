"""add circuit state version for stale probe protection

Revision ID: 0047_hotel_provider_circuit_state_version
Revises: 0046_hotel_provider_circuit
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0047_hotel_provider_circuit_state_version"
down_revision: Union[str, None] = "0046_hotel_provider_circuit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hotel_provider_circuit",
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("hotel_provider_circuit", "state_version")
