"""runs: add run_time

Penelope's `run.time`, copied into OrionDB so the run list can be served without
reading Penelope.

Revision ID: c7a4e1f9d2b6
Revises: b5e2d8c4f1a9
Create Date: 2026-11-23 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7a4e1f9d2b6"
down_revision: str | None = "b5e2d8c4f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: existing rows have no value until the Penelope run sync fills them in.
    op.add_column(
        "runs", sa.Column("run_time", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("runs", "run_time")
