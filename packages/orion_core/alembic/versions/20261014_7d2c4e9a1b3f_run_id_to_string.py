"""run_id columns uuid -> varchar, to match Penelope's text runId

Revision ID: 7d2c4e9a1b3f
Revises: 5b8e1f2a9c4d
Create Date: 2026-10-14 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d2c4e9a1b3f"
down_revision: str | None = "5b8e1f2a9c4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("cleaned_data", "estimated_car_state")


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            "run_id",
            existing_type=sa.UUID(),
            type_=sa.String(),
            postgresql_using="run_id::text",
        )


def downgrade() -> None:
    # Fails if any run_id isn't a valid UUID.
    for table in TABLES:
        op.alter_column(
            table,
            "run_id",
            existing_type=sa.String(),
            type_=sa.UUID(),
            postgresql_using="run_id::uuid",
        )
