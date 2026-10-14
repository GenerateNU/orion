"""sensors.unit nullable, rename sensor_sources.sourceDataTypeName

Revision ID: 5b8e1f2a9c4d
Revises: 209d00385e89
Create Date: 2026-10-13 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5b8e1f2a9c4d"
down_revision: str | None = "209d00385e89"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Unitless sensors (flags, states, normalized pedals) store NULL.
    op.alter_column("sensors", "unit", existing_type=sa.String(), nullable=True)
    # A rename, not drop+add, so existing rows survive.
    op.alter_column(
        "sensor_sources", "sourceDataTypeName", new_column_name="source_data_type_name"
    )


def downgrade() -> None:
    op.alter_column(
        "sensor_sources", "source_data_type_name", new_column_name="sourceDataTypeName"
    )
    # Fails if any unitless sensors were seeded; delete them first.
    op.alter_column("sensors", "unit", existing_type=sa.String(), nullable=False)
