"""Data access layer for span records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Span


async def bulk_create_spans(
    db: AsyncSession,
    spans: list[Span],
) -> int:
    """Insert multiple spans, skipping duplicates by span ID.

    Uses no_autoflush to prevent premature INSERT during duplicate checks,
    then flushes all new spans in a single batch.

    Returns the number of spans actually inserted.
    """
    inserted = 0
    with db.no_autoflush:
        for span in spans:
            existing = await db.execute(select(Span.id).where(Span.id == span.id))
            if existing.scalar_one_or_none() is None:
                db.add(span)
                inserted += 1

    await db.flush()
    return inserted


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
