"""add ukf_states

Revision ID: 1f974a596a38
Revises: 8b3d5f7a1c2e
Create Date: 2026-10-26 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1f974a596a38"
down_revision: str | None = "8b3d5f7a1c2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ukf_states",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("origin_lat", sa.FLOAT(), nullable=False),
        sa.Column("origin_lon", sa.FLOAT(), nullable=False),
        sa.Column("x", postgresql.ARRAY(sa.FLOAT()), nullable=False),
        sa.Column("p", postgresql.ARRAY(sa.FLOAT()), nullable=False),
        sa.Column("x_pred", postgresql.ARRAY(sa.FLOAT()), nullable=True),
        sa.Column("p_pred", postgresql.ARRAY(sa.FLOAT()), nullable=True),
        sa.Column("cross_cov", postgresql.ARRAY(sa.FLOAT()), nullable=True),
        sa.PrimaryKeyConstraint("run_id", "time", name=op.f("pk_ukf_states")),
    )


def downgrade() -> None:
    op.drop_table("ukf_states")
