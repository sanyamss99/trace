"""Read endpoints for traces and spans."""

from fastapi import APIRouter, Query

from api.dal import spans as span_dal
from api.dal import traces as trace_dal
from api.deps import DbSession, OrgId
from api.exceptions import InvalidCursorError, NotFoundError
from api.schemas.traces import (
    PaginatedTraceListResponse,
    SpanResponse,
    TraceDetailResponse,
    TraceListItem,
)

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=PaginatedTraceListResponse)
async def list_traces(
    db: DbSession,
    org_id: OrgId,
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None),
    function_name: str | None = None,
    environment: str | None = None,
    status: str | None = None,
) -> PaginatedTraceListResponse:
    """List traces for the authenticated organization (cursor-paginated)."""
    try:
        rows, next_cursor = await trace_dal.list_traces(
            db,
            org_id,
            limit=limit,
            cursor=cursor,
            function_name=function_name,
            environment=environment,
            status=status,
        )
    except ValueError as exc:
        raise InvalidCursorError() from exc

    items = []
    for row in rows:
        trace = row[0]
        span_count = row[1]
        items.append(
            TraceListItem(
                id=trace.id,
                function_name=trace.function_name,
                environment=trace.environment,
                started_at=trace.started_at,
                ended_at=trace.ended_at,
                duration_ms=trace.duration_ms,
                total_tokens=trace.total_tokens,
                total_cost_usd=(float(trace.total_cost_usd) if trace.total_cost_usd else None),
                status=trace.status,
                tags=trace.tags,
                span_count=span_count,
            )
        )

    return PaginatedTraceListResponse(
        traces=items,
        next_cursor=next_cursor,
        limit=limit,
    )


@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(
    trace_id: str,
    db: DbSession,
    org_id: OrgId,
) -> TraceDetailResponse:
    """Get a single trace with all its spans."""
    trace = await trace_dal.get_trace_by_id(db, trace_id, org_id)
    if not trace:
        raise NotFoundError("Trace", trace_id)

    spans = await span_dal.get_spans_by_trace(db, trace_id, org_id)

    return TraceDetailResponse(
        id=trace.id,
        function_name=trace.function_name,
        environment=trace.environment,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        duration_ms=trace.duration_ms,
        total_tokens=trace.total_tokens,
        total_cost_usd=float(trace.total_cost_usd) if trace.total_cost_usd else None,
        status=trace.status,
        tags=trace.tags,
        spans=[SpanResponse.model_validate(s, from_attributes=True) for s in spans],
    )


@router.get("/spans/{span_id}", response_model=SpanResponse)
async def get_span(
    span_id: str,
    db: DbSession,
    org_id: OrgId,
) -> SpanResponse:
    """Get a single span by ID."""
    span = await span_dal.get_span_by_id(db, span_id, org_id)
    if not span:
        raise NotFoundError("Span", span_id)

    return SpanResponse.model_validate(span, from_attributes=True)
