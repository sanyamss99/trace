"""Ingestion service — processes batches of spans from the SDK."""

from datetime import datetime
from itertools import groupby
from operator import attrgetter

from sqlalchemy.ext.asyncio import AsyncSession

from api.dal import spans as span_dal
from api.dal import traces as trace_dal
from api.logger import logger
from api.models import Span, UsageEvent
from api.schemas.ingest import SpanIngestPayload


class IngestResult:
    """Outcome of a batch ingestion."""

    def __init__(self, accepted: int, failed: int) -> None:
        self.accepted = accepted
        self.failed = failed


def _to_naive_utc(dt: datetime) -> datetime:
    """Strip timezone info for DB storage (SQLite stores naive datetimes)."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _map_span_to_orm(payload: SpanIngestPayload, org_id: str) -> Span:
    """Map SDK field names to the DB Span model fields."""
    end = payload.end_time or payload.start_time
    return Span(
        id=payload.span_id,
        trace_id=payload.trace_id,
        parent_span_id=payload.parent_span_id,
        org_id=org_id,
        function_name=payload.function_name,
        span_type=payload.span_type,
        model=payload.model,
        started_at=_to_naive_utc(payload.start_time),
        ended_at=_to_naive_utc(end),
        prompt_tokens=payload.prompt_tokens,
        completion_text=payload.completion_text,
        completion_tokens=payload.completion_tokens,
        completion_logprobs=payload.completion_logprobs,
        input_locals=payload.inputs,
        error=payload.error_message,
        span_metadata=payload.tags,
    )


def _compute_trace_aggregates(
    spans: list[SpanIngestPayload],
) -> dict:
    """Compute trace-level aggregates from a group of spans.

    Finds the root span (parent_span_id is None) for function_name,
    environment, and tags. Aggregates tokens and time window.
    """
    root_span = next((s for s in spans if s.parent_span_id is None), None)
    reference = root_span or spans[0]

    started_at = _to_naive_utc(min(s.start_time for s in spans))
    end_times = [s.end_time for s in spans if s.end_time is not None]
    ended_at = _to_naive_utc(max(end_times)) if end_times else started_at

    total_prompt = sum(s.prompt_tokens or 0 for s in spans)
    total_completion = sum(s.completion_tokens or 0 for s in spans)
    total_tokens = (total_prompt + total_completion) or None

    has_error = any(s.status == "error" for s in spans)
    status = "error" if has_error else "ok"

    return {
        "function_name": reference.function_name,
        "environment": reference.environment or "default",
        "started_at": started_at,
        "ended_at": ended_at,
        "total_tokens": total_tokens,
        "status": status,
        "tags": reference.tags,
    }


async def process_batch(
    db: AsyncSession,
    payloads: list[SpanIngestPayload],
    org_id: str,
) -> IngestResult:
    """Process a batch of SDK span payloads.

    Groups spans by trace_id, upserts trace records, bulk-inserts spans,
    and records a usage event. Each trace group uses a savepoint so that
    a failure in one group does not roll back the entire batch.
    """
    accepted = 0
    failed = 0

    sorted_payloads = sorted(payloads, key=attrgetter("trace_id"))
    for trace_id, group in groupby(sorted_payloads, key=attrgetter("trace_id")):
        group_spans = list(group)
        try:
            async with db.begin_nested():
                aggs = _compute_trace_aggregates(group_spans)

                await trace_dal.upsert_trace(
                    db,
                    trace_id=trace_id,
                    org_id=org_id,
                    function_name=aggs["function_name"],
                    environment=aggs["environment"],
                    started_at=aggs["started_at"],
                    ended_at=aggs["ended_at"],
                    total_tokens=aggs["total_tokens"],
                    status=aggs["status"],
                    tags=aggs["tags"],
                )

                orm_spans = [_map_span_to_orm(s, org_id) for s in group_spans]
                inserted = await span_dal.bulk_create_spans(db, orm_spans)
                accepted += inserted

        except Exception:
            logger.warning(
                "Failed to ingest trace group %s (%d spans)",
                trace_id,
                len(group_spans),
            )
            failed += len(group_spans)

    if accepted > 0:
        event = UsageEvent(
            org_id=org_id,
            event_type="span_ingested",
            quantity=accepted,
        )
        db.add(event)

    await db.commit()

    return IngestResult(accepted=accepted, failed=failed)
