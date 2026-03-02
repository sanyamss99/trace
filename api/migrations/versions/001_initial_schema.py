"""Initial schema — all core tables.

Revision ID: 001
Revises:
Create Date: 2026-03-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- organizations --
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("plan", sa.Text, server_default="hobby"),
        sa.Column("created_at", sa.DateTime),
    )

    # -- users --
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime),
    )

    # -- org_members --
    op.create_table(
        "org_members",
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.Text, nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime),
    )
    op.create_index("idx_org_members_user", "org_members", ["user_id"])

    # -- api_keys --
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key_hash", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text),
        sa.Column("created_at", sa.DateTime),
        sa.Column("last_used_at", sa.DateTime),
        sa.Column("revoked_at", sa.DateTime),
    )
    op.create_index("idx_api_keys_org", "api_keys", ["org_id"])

    # -- traces --
    op.create_table(
        "traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("function_name", sa.Text, nullable=False),
        sa.Column("environment", sa.Text, nullable=False, server_default="default"),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("ended_at", sa.DateTime, nullable=False),
        sa.Column("total_tokens", sa.Integer),
        sa.Column("total_cost_usd", sa.Numeric(10, 6)),
        sa.Column("status", sa.Text, server_default="success"),
        sa.Column("tags", sa.JSON),
    )
    op.create_index("idx_traces_org_started", "traces", ["org_id", "started_at"])
    op.create_index("idx_traces_org_env", "traces", ["org_id", "environment"])
    op.create_index("idx_traces_org_function", "traces", ["org_id", "function_name"])
    op.create_index("idx_traces_org_status", "traces", ["org_id", "status"])

    # -- spans --
    op.create_table(
        "spans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), sa.ForeignKey("traces.id"), nullable=False),
        sa.Column("parent_span_id", sa.String(36), sa.ForeignKey("spans.id")),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("function_name", sa.Text, nullable=False),
        sa.Column("span_type", sa.Text, server_default="llm"),
        sa.Column("model", sa.Text),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("ended_at", sa.DateTime, nullable=False),
        sa.Column("prompt_text", sa.Text),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_text", sa.Text),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("completion_logprobs", sa.JSON),
        sa.Column("cost_usd", sa.Numeric(10, 6)),
        sa.Column("model_params", sa.JSON),
        sa.Column("input_locals", sa.JSON),
        sa.Column("error", sa.Text),
        sa.Column("metadata", sa.JSON),
    )
    op.create_index("idx_spans_trace_id", "spans", ["trace_id"])
    op.create_index("idx_spans_org_started", "spans", ["org_id", "started_at"])

    # -- span_segments --
    op.create_table(
        "span_segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("span_id", sa.String(36), sa.ForeignKey("spans.id"), nullable=False),
        sa.Column("segment_name", sa.Text, nullable=False),
        sa.Column("segment_type", sa.Text, nullable=False),
        sa.Column("segment_text", sa.Text, nullable=False),
        sa.Column("position_start", sa.Integer),
        sa.Column("position_end", sa.Integer),
        sa.Column("retrieval_rank", sa.Integer),
        sa.Column("influence_score", sa.Numeric(5, 4)),
        sa.Column("utilization_score", sa.Numeric(5, 4)),
        sa.Column("attribution_method", sa.Text),
        sa.UniqueConstraint("span_id", "segment_name", name="uq_span_segment"),
    )
    op.create_index("idx_span_segments_span_id", "span_segments", ["span_id"])

    # -- usage_events --
    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("occurred_at", sa.DateTime),
        sa.Column("quantity", sa.Integer, server_default="1"),
    )
    op.create_index("idx_usage_org_occurred", "usage_events", ["org_id", "occurred_at"])


def downgrade() -> None:
    op.drop_table("usage_events")
    op.drop_table("span_segments")
    op.drop_table("spans")
    op.drop_table("traces")
    op.drop_table("api_keys")
    op.drop_table("org_members")
    op.drop_table("users")
    op.drop_table("organizations")
