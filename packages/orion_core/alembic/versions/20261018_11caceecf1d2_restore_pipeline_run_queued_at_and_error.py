"""pipeline_runs: restore queued_at and error, drop updated_at

209d00385e89 dropped both columns, but the job queue orders by queued_at and
records failures in error.

Revision ID: 11caceecf1d2
Revises: 7d2c4e9a1b3f
Create Date: 2026-10-18 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "11caceecf1d2"
down_revision: str | None = "7d2c4e9a1b3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column("pipeline_runs", sa.Column("error", sa.String(), nullable=True))
    # Keep existing jobs' original order instead of stamping them all with now().
    op.execute("UPDATE pipeline_runs SET queued_at = updated_at")
    op.drop_column("pipeline_runs", "updated_at")


def downgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute("UPDATE pipeline_runs SET updated_at = queued_at")
    op.drop_column("pipeline_runs", "error")
    op.drop_column("pipeline_runs", "queued_at")
