"""add pipeline_runs.step

A job can run one step instead of the whole pipeline. Null means the whole
pipeline, so existing jobs keep their meaning.

Revision ID: 06afef2868d4
Revises: b5e2d8c4f1a9
Create Date: 2026-11-15 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "06afef2868d4"
down_revision: str | None = "b5e2d8c4f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pipeline_runs", sa.Column("step", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("pipeline_runs", "step")
