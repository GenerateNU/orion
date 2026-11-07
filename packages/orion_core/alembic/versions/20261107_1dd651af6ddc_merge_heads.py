"""merge heads

Revision ID: 1dd651af6ddc
Revises: 1f974a596a38, 466a05a95692
Create Date: 2026-11-07 18:28:17.092341+00:00

"""

from collections.abc import Sequence

revision: str = "1dd651af6ddc"
down_revision: str | None = ("1f974a596a38", "466a05a95692")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
