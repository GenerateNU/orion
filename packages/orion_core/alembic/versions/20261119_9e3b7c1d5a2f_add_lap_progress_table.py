"""add lap_progress table

The lap progress step writes its own table instead of filling in
estimated_car_state.lap_percent. Existing percentages are dropped; re-run the
pipeline to fill the new table.

Revision ID: 9e3b7c1d5a2f
Revises: 4c28068e3526
Create Date: 2026-11-19 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9e3b7c1d5a2f"
down_revision: str | None = "4c28068e3526"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lap_progress",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("lap_id", sa.Integer(), nullable=False),
        sa.Column("lap_percent", sa.FLOAT(), nullable=True),
        sa.PrimaryKeyConstraint("run_id", "time", name=op.f("pk_lap_progress")),
    )
    op.drop_column("estimated_car_state", "lap_percent")


def downgrade() -> None:
    op.add_column(
        "estimated_car_state",
        sa.Column("lap_percent", sa.FLOAT(), nullable=True),
    )
    op.drop_table("lap_progress")
