"""SQLAlchemy ORM models for all Trace database tables."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from api.constants import STATUS_OK


def _naive_utcnow() -> datetime:
    """Return current UTC time as a naive datetime (no tzinfo).

    Postgres TIMESTAMP WITHOUT TIME ZONE columns reject timezone-aware
    datetimes. This helper produces naive UTC values safe for storage.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


class Organization(Base):
    """Multi-tenancy root — every user belongs to one."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[str] = mapped_column(Text, default="hobby")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utcnow)

    # Relationships
    members: Mapped[list["OrgMember"]] = relationship(back_populates="organization")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="organization")
    traces: Mapped[list["Trace"]] = relationship(back_populates="organization")
    usage_events: Mapped[list["UsageEvent"]] = relationship(back_populates="organization")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    """Application users — identified by email."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utcnow)

    # Relationships
    memberships: Mapped[list["OrgMember"]] = relationship(back_populates="user")
    created_api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="created_by_user")


# ---------------------------------------------------------------------------
# Org Members (composite PK)
# ---------------------------------------------------------------------------


class OrgMember(Base):
    """Maps users to organizations with a role."""

    __tablename__ = "org_members"

    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utcnow)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")

    __table_args__ = (Index("idx_org_members_user", "user_id"),)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


class ApiKey(Base):
    """API keys scoped to an organization — survives employee churn."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="api_keys")
    created_by_user: Mapped["User"] = relationship(back_populates="created_api_keys")

    __table_args__ = (Index("idx_api_keys_org", "org_id"),)


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------


class Trace(Base):
    """Top-level trace record for a decorated function invocation."""

    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    function_name: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    status: Mapped[str] = mapped_column(Text, default=STATUS_OK)
    tags: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="traces")
    spans: Mapped[list["Span"]] = relationship(back_populates="trace")

    @hybrid_property
    def duration_ms(self) -> int | None:
        """Compute duration in milliseconds from started_at/ended_at."""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    __table_args__ = (
        Index("idx_traces_org_started", "org_id", "started_at"),
        Index("idx_traces_org_env", "org_id", "environment"),
        Index("idx_traces_org_function", "org_id", "function_name"),
        Index("idx_traces_org_status", "org_id", "status"),
    )


# ---------------------------------------------------------------------------
# Spans
# ---------------------------------------------------------------------------


class Span(Base):
    """Individual LLM / retrieval / custom call within a trace."""

    __tablename__ = "spans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    trace_id: Mapped[str] = mapped_column(String(36), ForeignKey("traces.id"), nullable=False)
    parent_span_id: Mapped[str | None] = mapped_column(String(36))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    function_name: Mapped[str] = mapped_column(Text, nullable=False)
    span_type: Mapped[str] = mapped_column(Text, default="llm")
    model: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_text: Mapped[str | None] = mapped_column(Text)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_logprobs: Mapped[list | None] = mapped_column(JSON)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    model_params: Mapped[dict | None] = mapped_column(JSON)
    input_locals: Mapped[dict | None] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    span_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)

    # Relationships
    trace: Mapped["Trace"] = relationship(back_populates="spans")
    segments: Mapped[list["SpanSegment"]] = relationship(back_populates="span")

    @hybrid_property
    def duration_ms(self) -> int | None:
        """Compute duration in milliseconds from started_at/ended_at."""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    __table_args__ = (
        Index("idx_spans_trace_id", "trace_id"),
        Index("idx_spans_org_started", "org_id", "started_at"),
    )


# ---------------------------------------------------------------------------
# Span Segments (attribution results)
# ---------------------------------------------------------------------------


class SpanSegment(Base):
    """Attribution results for a segment of a span's prompt."""

    __tablename__ = "span_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    span_id: Mapped[str] = mapped_column(String(36), ForeignKey("spans.id"), nullable=False)
    segment_name: Mapped[str] = mapped_column(Text, nullable=False)
    segment_type: Mapped[str] = mapped_column(Text, nullable=False)
    segment_text: Mapped[str] = mapped_column(Text, nullable=False)
    position_start: Mapped[int | None] = mapped_column(Integer)
    position_end: Mapped[int | None] = mapped_column(Integer)
    retrieval_rank: Mapped[int | None] = mapped_column(Integer)
    influence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    utilization_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    attribution_method: Mapped[str | None] = mapped_column(Text)

    # Relationships
    span: Mapped["Span"] = relationship(back_populates="segments")

    __table_args__ = (
        UniqueConstraint("span_id", "segment_name", name="uq_span_segment"),
        Index("idx_span_segments_span_id", "span_id"),
    )


# ---------------------------------------------------------------------------
# Usage Events
# ---------------------------------------------------------------------------


class UsageEvent(Base):
    """Metered billing events scoped to an organization."""

    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utcnow)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="usage_events")

    __table_args__ = (Index("idx_usage_org_occurred", "org_id", "occurred_at"),)
