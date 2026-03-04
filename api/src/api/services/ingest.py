"""Ingestion service — processes batches of spans from the SDK."""

from datetime import UTC, datetime
from itertools import groupby
from operator import attrgetter

from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.constants import STATUS_ERROR, STATUS_OK
from api.dal import spans as span_dal
from api.dal import traces as trace_dal
from api.logger import logger
from api.models import Span, UsageEvent
from api.schemas.ingest import SpanIngestPayload
from api.services.attribution import compute_attribution
from api.services.cost import compute_cost


class IngestResult:
    """Outcome of a batch ingestion."""

    def __init__(self, accepted: int, failed: int) -> None:
        self.accepted = accepted
        self.failed = failed


def _to_naive_utc(dt: datetime) -> datetime:
    """Convert a datetime to a naive UTC datetime for DB storage.

    - Naive datetimes are assumed to already be UTC.
    - Aware datetimes are converted to UTC first, then stripped.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _map_span_to_orm(payload: SpanIngestPayload, org_id: str) -> Span:
    """Map SDK field names to the DB Span model fields."""
    end = payload.end_time or payload.start_time
    cost = compute_cost(payload.model, payload.prompt_tokens, payload.completion_tokens)
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
        prompt_text=payload.prompt_text,
        prompt_tokens=payload.prompt_tokens,
        completion_text=payload.completion_text,
        completion_tokens=payload.completion_tokens,
        completion_logprobs=payload.completion_logprobs,
        cost_usd=cost,
        input_locals=payload.inputs,
        output=payload.output,
        error=payload.error_message,
        span_metadata=payload.tags,
    )


def _compute_trace_aggregates(
    spans: list[SpanIngestPayload],
) -> dict:
    """Compute trace-level aggregates from a group of spans.

    Finds the root span (parent_span_id is None) for function_name,
    environment, and tags. Aggregates tokens, cost, and time window.
    """
    root_span = next((s for s in spans if s.parent_span_id is None), None)
    reference = root_span or spans[0]

    started_at = _to_naive_utc(min(s.start_time for s in spans))
    end_times = [s.end_time for s in spans if s.end_time is not None]
    ended_at = _to_naive_utc(max(end_times)) if end_times else started_at

    total_prompt = sum(s.prompt_tokens or 0 for s in spans)
    total_completion = sum(s.completion_tokens or 0 for s in spans)
    total_tokens = (total_prompt + total_completion) or None

    # Aggregate cost across all spans with known models
    span_costs = [compute_cost(s.model, s.prompt_tokens, s.completion_tokens) for s in spans]
    non_null_costs = [c for c in span_costs if c is not None]
    total_cost = sum(non_null_costs) if non_null_costs else None

    has_error = any(s.status == STATUS_ERROR for s in spans)
    status = STATUS_ERROR if has_error else STATUS_OK

    return {
        "function_name": reference.function_name,
        "environment": reference.environment or "default",
        "started_at": started_at,
        "ended_at": ended_at,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost,
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
                    total_cost_usd=aggs["total_cost_usd"],
                    status=aggs["status"],
                    tags=aggs["tags"],
                )

                orm_spans = [_map_span_to_orm(s, org_id) for s in group_spans]
                inserted = await span_dal.bulk_create_spans(db, orm_spans)
                accepted += inserted

                # Auto-compute attribution for LLM spans with prompt_text
                for span in orm_spans:
                    if span.span_type == "llm" and span.prompt_text:
                        try:
                            await compute_attribution(db, span.id, org_id)
                        except Exception:
                            logger.debug(
                                "Auto-attribution skipped span_id=%s",
                                span.id,
                            )

        except (IntegrityError, DBAPIError) as exc:
            logger.warning(
                "Failed to ingest trace group org_id=%s trace_id=%s (%d spans): %s",
                org_id,
                trace_id,
                len(group_spans),
                type(exc).__name__,
                exc_info=settings.is_debug,
            )
            failed += len(group_spans)
        except OperationalError:
            logger.error(
                "DB operational error during ingest org_id=%s trace_id=%s",
                org_id,
                trace_id,
                exc_info=True,
            )
            raise

    if accepted > 0:
        event = UsageEvent(
            org_id=org_id,
            event_type="span_ingested",
            quantity=accepted,
        )
        db.add(event)

    return IngestResult(accepted=accepted, failed=failed)
