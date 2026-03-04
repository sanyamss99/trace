"""Add output JSON column to spans table.

The SDK sends output data for each span, but the API was silently
dropping it. This migration adds the column to persist it.

Revision ID: 003
Revises: 002
Create Date: 2026-03-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("spans", sa.Column("output", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("spans", "output")
