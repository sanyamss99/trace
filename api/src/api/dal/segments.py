"""Data access layer for span segment records."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import SpanSegment


async def get_segments_by_span(
    db: AsyncSession,
    span_id: str,
) -> list[SpanSegment]:
    """Fetch all segments for a span, ordered by position_start."""
    result = await db.execute(
        select(SpanSegment)
        .where(SpanSegment.span_id == span_id)
        .order_by(SpanSegment.position_start)
    )
    return list(result.scalars().all())


async def get_segments_by_span_ids(
    db: AsyncSession,
    span_ids: list[str],
) -> list[SpanSegment]:
    """Fetch all segments for multiple spans."""
    if not span_ids:
        return []
    result = await db.execute(
        select(SpanSegment)
        .where(SpanSegment.span_id.in_(span_ids))
        .order_by(SpanSegment.span_id, SpanSegment.position_start)
    )
    return list(result.scalars().all())


async def bulk_upsert_segments(
    db: AsyncSession,
    segments: list[SpanSegment],
) -> int:
    """Upsert segments via ON CONFLICT on (span_id, segment_name).

    Updates scores and text on conflict.  Returns number affected.
    """
    if not segments:
        return 0

    values = [
        {
            "id": s.id,
            "span_id": s.span_id,
            "segment_name": s.segment_name,
            "segment_type": s.segment_type,
            "segment_text": s.segment_text,
            "position_start": s.position_start,
            "position_end": s.position_end,
            "retrieval_rank": s.retrieval_rank,
            "influence_score": s.influence_score,
            "utilization_score": s.utilization_score,
            "attribution_method": s.attribution_method,
        }
        for s in segments
    ]

    stmt = pg_insert(SpanSegment.__table__).values(values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_span_segment",
        set_={
            "segment_text": stmt.excluded.segment_text,
            "position_start": stmt.excluded.position_start,
            "position_end": stmt.excluded.position_end,
            "retrieval_rank": stmt.excluded.retrieval_rank,
            "influence_score": stmt.excluded.influence_score,
            "utilization_score": stmt.excluded.utilization_score,
            "attribution_method": stmt.excluded.attribution_method,
        },
    )
    result = await db.execute(stmt)
    return result.rowcount


async def delete_segments_by_span(
    db: AsyncSession,
    span_id: str,
) -> int:
    """Delete all segments for a span.  Returns count deleted."""
    result = await db.execute(delete(SpanSegment).where(SpanSegment.span_id == span_id))
    return result.rowcount
