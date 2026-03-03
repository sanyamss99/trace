"""Data access layer for trace records."""

from datetime import datetime

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Span, Trace


async def upsert_trace(
    db: AsyncSession,
    *,
    trace_id: str,
    org_id: str,
    function_name: str,
    environment: str,
    started_at: datetime,
    ended_at: datetime,
    total_tokens: int | None,
    status: str,
    tags: dict | None,
) -> None:
    """Insert a new trace or update an existing one.

    On conflict: widen time window, accumulate tokens, escalate status
    to 'error' if any span errored, and update function_name/environment/tags.
    """
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    trace = result.scalar_one_or_none()

    if trace is None:
        trace = Trace(
            id=trace_id,
            org_id=org_id,
            function_name=function_name,
            environment=environment,
            started_at=started_at,
            ended_at=ended_at,
            total_tokens=total_tokens,
            status=status,
            tags=tags,
        )
        db.add(trace)
    else:
        if started_at < trace.started_at:
            trace.started_at = started_at
        if ended_at > trace.ended_at:
            trace.ended_at = ended_at
        if total_tokens is not None:
            trace.total_tokens = (trace.total_tokens or 0) + total_tokens
        if status == "error":
            trace.status = "error"
        if function_name:
            trace.function_name = function_name
        if environment:
            trace.environment = environment
        if tags:
            trace.tags = tags


async def get_trace_by_id(
    db: AsyncSession,
    trace_id: str,
    org_id: str,
) -> Trace | None:
    """Fetch a single trace by ID, scoped to org."""
    result = await db.execute(select(Trace).where(Trace.id == trace_id, Trace.org_id == org_id))
    return result.scalar_one_or_none()


async def list_traces(
    db: AsyncSession,
    org_id: str,
    *,
    page: int = 1,
    page_size: int = 50,
    function_name: str | None = None,
    environment: str | None = None,
    status: str | None = None,
) -> tuple[list[Row], int]:
    """List traces for an org with optional filters and pagination.

    Returns (rows_with_span_count, total_count).
    Each row has .Trace and .span_count attributes.
    """
    span_count_subq = (
        select(func.count(Span.id))
        .where(Span.trace_id == Trace.id)
        .correlate(Trace)
        .scalar_subquery()
        .label("span_count")
    )

    base_filter = select(Trace).where(Trace.org_id == org_id)
    if function_name:
        base_filter = base_filter.where(Trace.function_name == function_name)
    if environment:
        base_filter = base_filter.where(Trace.environment == environment)
    if status:
        base_filter = base_filter.where(Trace.status == status)

    # Total count
    count_q = select(func.count()).select_from(base_filter.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Fetch page with span_count
    query = select(Trace, span_count_subq).where(Trace.org_id == org_id)
    if function_name:
        query = query.where(Trace.function_name == function_name)
    if environment:
        query = query.where(Trace.environment == environment)
    if status:
        query = query.where(Trace.status == status)

    query = query.order_by(Trace.started_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    return rows, total
