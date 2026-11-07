"""drop estimated_car_state.lap_id

Laps live in their own `laps` table now; the state step writes positions only.

Revision ID: b5e2d8c4f1a9
Revises: 1dd651af6ddc
Create Date: 2026-11-07 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5e2d8c4f1a9"
down_revision: str | None = "1dd651af6ddc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("estimated_car_state", "lap_id")


def downgrade() -> None:
    # Existing rows have no lap to restore, so backfill 0 to satisfy NOT NULL.
    op.add_column(
        "estimated_car_state",
        sa.Column("lap_id", sa.INTEGER(), nullable=False, server_default="0"),
    )
    op.alter_column("estimated_car_state", "lap_id", server_default=None)
