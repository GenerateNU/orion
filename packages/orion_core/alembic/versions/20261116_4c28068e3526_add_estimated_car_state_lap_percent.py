"""add estimated_car_state.lap_percent

Written by the lap progress step. Existing rows get NULL.

Revision ID: 4c28068e3526
Revises: b5e2d8c4f1a9
Create Date: 2026-11-16 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4c28068e3526"
down_revision: str | None = "b5e2d8c4f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "estimated_car_state",
        sa.Column("lap_percent", sa.FLOAT(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("estimated_car_state", "lap_percent")
