"""runs: add start_time and end_time

Revision ID: 8b3d5f7a1c2e
Revises: 4f1a8c6e2d7b
Create Date: 2026-10-16 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b3d5f7a1c2e"
down_revision: str | None = "4f1a8c6e2d7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: a run row is created when its first job is queued, before the
    # clean step has read any data to set its bounds.
    op.add_column(
        "runs", sa.Column("start_time", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "runs", sa.Column("end_time", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("runs", "end_time")
    op.drop_column("runs", "start_time")
