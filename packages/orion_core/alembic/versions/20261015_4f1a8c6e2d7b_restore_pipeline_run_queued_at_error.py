"""pipeline_runs: restore queued_at and error, drop unused updated_at

Revision ID: 4f1a8c6e2d7b
Revises: 7d2c4e9a1b3f
Create Date: 2026-10-15 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f1a8c6e2d7b"
down_revision: str | None = "7d2c4e9a1b3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # updated_at was only ever set on insert, so it already holds the queue time.
    op.alter_column("pipeline_runs", "updated_at", new_column_name="queued_at")
    op.add_column("pipeline_runs", sa.Column("error", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("pipeline_runs", "error")
    op.alter_column("pipeline_runs", "queued_at", new_column_name="updated_at")
