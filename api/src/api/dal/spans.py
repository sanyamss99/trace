"""Data access layer for span records."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Span


async def bulk_create_spans(
    db: AsyncSession,
    spans: list[Span],
) -> int:
    """Insert multiple spans, skipping duplicates via ON CONFLICT DO NOTHING.

    Returns the number of spans actually inserted.
    """
    if not spans:
        return 0

    values = [
        {
            "id": s.id,
            "trace_id": s.trace_id,
            "parent_span_id": s.parent_span_id,
            "org_id": s.org_id,
            "function_name": s.function_name,
            "span_type": s.span_type,
            "model": s.model,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "prompt_text": s.prompt_text,
            "prompt_tokens": s.prompt_tokens,
            "completion_text": s.completion_text,
            "completion_tokens": s.completion_tokens,
            "completion_logprobs": s.completion_logprobs,
            "cost_usd": s.cost_usd,
            "model_params": s.model_params,
            "input_locals": s.input_locals,
            "output": s.output,
            "error": s.error,
            "metadata": s.span_metadata,
        }
        for s in spans
    ]

    stmt = pg_insert(Span.__table__).values(values).on_conflict_do_nothing(index_elements=["id"])
    result = await db.execute(stmt)
    return result.rowcount


async def get_spans_by_trace(
    db: AsyncSession,
    trace_id: str,
    org_id: str,
) -> list[Span]:
    """Fetch all spans for a trace, ordered by started_at."""
    result = await db.execute(
        select(Span)
        .where(Span.trace_id == trace_id, Span.org_id == org_id)
        .order_by(Span.started_at)
    )
    return list(result.scalars().all())


async def get_span_by_id(
    db: AsyncSession,
    span_id: str,
    org_id: str,
) -> Span | None:
    """Fetch a single span by ID, scoped to org."""
    result = await db.execute(select(Span).where(Span.id == span_id, Span.org_id == org_id))
    return result.scalar_one_or_none()
