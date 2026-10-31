"""copy penelope

Revision ID: c2aea7d53185
Revises: 1f974a596a38
Create Date: 2026-10-31 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2aea7d53185"
down_revision: str | None = "1f974a596a38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A copy of Penelope's tables, filled by `orion-pipeline sync`. Columns match
# orion_core/models/penelope/penelope_tables.py. Alembic only autogenerates
# against the default schema, so it never tries to drop these.
SCHEMA = "penelope"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA {SCHEMA}")
    op.create_table(
        "run",
        # table format from packages/orion_core/src/orion_core/models/penelope/penelope_tables.py
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("runId", sa.Integer(), nullable=True),
        sa.Column("driverName", sa.String(), nullable=True),
        sa.Column("locationName", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_run"),
        schema=SCHEMA,
    )
    op.create_table(
        "data_type",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("name", name="pk_data_type"),
        schema=SCHEMA,
    )
    op.create_table(
        "data",
        sa.Column("dataTypeName", sa.String(), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("runId", sa.String(), nullable=False),
        sa.Column(
            "values", postgresql.ARRAY(postgresql.DOUBLE_PRECISION()), nullable=True
        ),
        # runId first (Penelope has time first) so per-run reads and the sync's
        # "where did this run leave off" lookup are index scans.
        sa.PrimaryKeyConstraint("runId", "time", "dataTypeName", name="pk_data"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
