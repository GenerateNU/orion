"""add lap_progress table

Revision ID: a0b83adc3141
Revises: b5e2d8c4f1a9
Create Date: 2026-11-22 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0b83adc3141"
down_revision: str | None = "b5e2d8c4f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lap_progress",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("lap_id", sa.Integer(), nullable=False),
        sa.Column("lap_percent", sa.FLOAT(), nullable=False),
        sa.PrimaryKeyConstraint("run_id", "time", name=op.f("pk_lap_progress")),
    )


def downgrade() -> None:
    op.drop_table("lap_progress")
