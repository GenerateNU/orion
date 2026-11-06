"""add metrics

Revision ID: 06ca92b6ba37
Revises: 1f974a596a38
Create Date: 2026-11-01 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "06ca92b6ba37"
down_revision: str | None = "1f974a596a38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metrics",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("lap_number", sa.INTEGER(), nullable=False),
        sa.Column("startTime", sa.DateTime(), nullable=False),
        sa.Column("endTime", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("run_id", "lap_number", name=op.f("pk_metrics")),
    )


def downgrade() -> None:
    op.drop_table("metrics")
