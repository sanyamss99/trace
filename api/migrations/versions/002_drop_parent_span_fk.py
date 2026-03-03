"""Drop self-referential FK on spans.parent_span_id.

Spans arrive out of order across batches — the SDK's FlushWorker
batches by time/size, not by trace boundaries. A child span can arrive
before its parent, which violates the FK constraint on Postgres.

The parent-child relationship is informational (used to build span
trees at query time), not a data integrity requirement.

Revision ID: 002
Revises: 001
Create Date: 2026-03-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("spans_parent_span_id_fkey", "spans", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key("spans_parent_span_id_fkey", "spans", "spans", ["parent_span_id"], ["id"])
