"""add graph_tabs table

Revision ID: 6e4a1c9d3b72
Revises: b5e2d8c4f1a9
Create Date: 2026-11-20 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6e4a1c9d3b72"
down_revision: str | None = "b5e2d8c4f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graph_tabs",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("tabs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_graph_tabs")),
    )


def downgrade() -> None:
    op.drop_table("graph_tabs")
