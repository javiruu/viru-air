from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0060_revalidation_job_active_target"
down_revision: Union[str, None] = "0059_hotel_tracking_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    jobs = sa.table(
        "revalidation_job",
        sa.column("id", sa.String(length=36)),
        sa.column("job_type", sa.String(length=32)),
        sa.column("target_type", sa.String(length=16)),
        sa.column("target_fingerprint", sa.String(length=64)),
        sa.column("provider", sa.String(length=40)),
        sa.column("status", sa.String(length=16)),
        sa.column("created_at", sa.DateTime()),
    )
    active = bind.execute(
        sa.select(
            jobs.c.id,
            jobs.c.job_type,
            jobs.c.target_type,
            jobs.c.target_fingerprint,
            jobs.c.provider,
        )
        .where(jobs.c.status.in_(["queued", "running"]))
        .order_by(jobs.c.created_at.desc(), jobs.c.id.desc())
    ).mappings()
    seen: set[tuple[str, str, str, str | None]] = set()
    for row in active:
        key = (row["job_type"], row["target_type"], row["target_fingerprint"], row["provider"])
        if key in seen:
            bind.execute(
                jobs.update()
                .where(jobs.c.id == row["id"])
                .values(status="failed")
            )
        else:
            seen.add(key)

    op.create_index(
        "uq_revalidation_job_active_target",
        "revalidation_job",
        ["job_type", "target_type", "target_fingerprint", sa.text("coalesce(provider, '')")],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_revalidation_job_active_target", table_name="revalidation_job")
