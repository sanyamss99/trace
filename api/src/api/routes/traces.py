"""Read endpoints for traces and spans."""

import statistics
from datetime import datetime

from fastapi import APIRouter, Query

from api.dal import segments as segment_dal
from api.dal import spans as span_dal
from api.dal import traces as trace_dal
from api.deps import DbSession, OrgId
from api.exceptions import InvalidCursorError, NotFoundError
from api.models import Span
from api.schemas.traces import (
    AttributionResponse,
    FunctionCostItem,
    FunctionDetailResponse,
    LatencyPercentiles,
    ModelCostItem,
    OverviewStatsResponse,
    PaginatedTraceListResponse,
    SpanResponse,
    SpanSegmentResponse,
    TimeSeriesPoint,
    TraceDetailResponse,
    TraceListItem,
)
from api.services.attribution import compute_attribution

router = APIRouter(prefix="/traces", tags=["traces"])


def _build_span_response(
    span: Span,
    segments: list[SpanSegmentResponse] | None = None,
) -> SpanResponse:
    """Build SpanResponse from Span ORM without triggering relationship lazy loads."""
    return SpanResponse(
        id=span.id,
        trace_id=span.trace_id,
        parent_span_id=span.parent_span_id,
        function_name=span.function_name,
        span_type=span.span_type,
        model=span.model,
        started_at=span.started_at,
        ended_at=span.ended_at,
        duration_ms=span.duration_ms,
        prompt_text=span.prompt_text,
        prompt_tokens=span.prompt_tokens,
        completion_tokens=span.completion_tokens,
        completion_text=span.completion_text,
        completion_logprobs=span.completion_logprobs,
        cost_usd=float(span.cost_usd) if span.cost_usd else None,
        input_locals=span.input_locals,
        output=span.output,
        error=span.error,
        span_metadata=span.span_metadata,
        segments=segments or [],
    )


@router.get("", response_model=PaginatedTraceListResponse)
async def list_traces(
    db: DbSession,
    org_id: OrgId,
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None),
    function_name: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
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
            started_after=started_after,
            started_before=started_before,
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


@router.get("/analytics/overview", response_model=OverviewStatsResponse)
async def get_overview_stats(
    db: DbSession,
    org_id: OrgId,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    environment: str | None = None,
) -> OverviewStatsResponse:
    """Get dashboard overview stats: totals, averages, error rate."""
    row = await trace_dal.overview_stats(
        db,
        org_id,
        started_after=started_after,
        started_before=started_before,
        environment=environment,
    )
    trace_count = row.trace_count if row else 0
    error_count = (row.error_count or 0) if row else 0
    error_rate = (error_count / trace_count) if trace_count > 0 else 0.0
    return OverviewStatsResponse(
        trace_count=trace_count,
        total_tokens=row.total_tokens if row else None,
        total_cost_usd=float(row.total_cost_usd) if row and row.total_cost_usd else None,
        avg_duration_ms=float(row.avg_duration_ms) if row and row.avg_duration_ms else None,
        error_count=error_count,
        error_rate=round(error_rate, 4),
    )


@router.get("/analytics/timeseries", response_model=list[TimeSeriesPoint])
async def get_timeseries(
    db: DbSession,
    org_id: OrgId,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    environment: str | None = None,
) -> list[TimeSeriesPoint]:
    """Get daily trace count, cost, and error count over time."""
    rows = await trace_dal.traces_over_time(
        db,
        org_id,
        started_after=started_after,
        started_before=started_before,
        environment=environment,
    )
    return [
        TimeSeriesPoint(
            date=str(row.date),
            trace_count=row.trace_count,
            total_cost_usd=float(row.total_cost_usd) if row.total_cost_usd else None,
            error_count=row.error_count,
        )
        for row in rows
    ]


@router.get("/analytics/cost-by-function", response_model=list[FunctionCostItem])
async def get_cost_by_function(
    db: DbSession,
    org_id: OrgId,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    environment: str | None = None,
) -> list[FunctionCostItem]:
    """Get cost and usage aggregates grouped by function name."""
    rows = await trace_dal.cost_by_function(
        db,
        org_id,
        started_after=started_after,
        started_before=started_before,
        environment=environment,
    )
    return [
        FunctionCostItem(
            function_name=row.function_name,
            call_count=row.call_count,
            total_tokens=row.total_tokens,
            total_cost_usd=float(row.total_cost_usd) if row.total_cost_usd else None,
            avg_cost_usd=float(row.avg_cost_usd) if row.avg_cost_usd else None,
            avg_duration_ms=float(row.avg_duration_ms) if row.avg_duration_ms else None,
            error_count=row.error_count,
            avg_quality_score=float(row.avg_quality_score) if row.avg_quality_score else None,
        )
        for row in rows
    ]


@router.get("/analytics/function-detail", response_model=FunctionDetailResponse)
async def get_function_detail(
    db: DbSession,
    org_id: OrgId,
    function_name: str = Query(..., description="Function name to get details for"),
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    environment: str | None = None,
) -> FunctionDetailResponse:
    """Get latency percentiles and recent call statuses for a function."""
    data = await trace_dal.function_detail(
        db,
        org_id,
        function_name,
        started_after=started_after,
        started_before=started_before,
        environment=environment,
    )
    durations: list[float] = data["durations"]

    if len(durations) == 0:
        percentiles = LatencyPercentiles(p50=None, p90=None, p99=None)
    elif len(durations) == 1:
        val = durations[0]
        percentiles = LatencyPercentiles(p50=val, p90=val, p99=val)
    else:
        qs = statistics.quantiles(durations, n=100, method="inclusive")
        percentiles = LatencyPercentiles(
            p50=round(qs[49], 2),
            p90=round(qs[89], 2),
            p99=round(qs[98], 2),
        )

    return FunctionDetailResponse(
        function_name=function_name,
        percentiles=percentiles,
        recent_statuses=data["recent_statuses"],
    )


@router.get("/analytics/cost-by-model", response_model=list[ModelCostItem])
async def get_cost_by_model(
    db: DbSession,
    org_id: OrgId,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    environment: str | None = None,
    function_name: str | None = None,
) -> list[ModelCostItem]:
    """Get cost and usage aggregates grouped by model name."""
    rows = await trace_dal.cost_by_model(
        db,
        org_id,
        started_after=started_after,
        started_before=started_before,
        environment=environment,
        function_name=function_name,
    )
    return [
        ModelCostItem(
            model=row.model,
            call_count=row.call_count,
            total_tokens=row.total_tokens,
            total_cost_usd=float(row.total_cost_usd) if row.total_cost_usd else None,
            avg_cost_usd=float(row.avg_cost_usd) if row.avg_cost_usd else None,
            avg_quality_score=float(row.avg_quality_score) if row.avg_quality_score else None,
        )
        for row in rows
    ]


@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(
    trace_id: str,
    db: DbSession,
    org_id: OrgId,
) -> TraceDetailResponse:
    """Get a single trace with all its spans and their segments."""
    trace = await trace_dal.get_trace_by_id(db, trace_id, org_id)
    if not trace:
        raise NotFoundError("Trace", trace_id)

    spans = await span_dal.get_spans_by_trace(db, trace_id, org_id)

    # Bulk-load segments for all spans to avoid N+1 queries
    span_ids = [s.id for s in spans]
    all_segments = await segment_dal.get_segments_by_span_ids(db, span_ids)
    segments_by_span: dict[str, list[SpanSegmentResponse]] = {}
    for seg in all_segments:
        segments_by_span.setdefault(seg.span_id, []).append(
            SpanSegmentResponse.model_validate(seg, from_attributes=True)
        )

    span_responses = [_build_span_response(s, segments_by_span.get(s.id, [])) for s in spans]

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
        spans=span_responses,
    )


@router.get("/spans/{span_id}", response_model=SpanResponse)
async def get_span(
    span_id: str,
    db: DbSession,
    org_id: OrgId,
) -> SpanResponse:
    """Get a single span by ID, including any computed segments."""
    span = await span_dal.get_span_by_id(db, span_id, org_id)
    if not span:
        raise NotFoundError("Span", span_id)

    segments = await segment_dal.get_segments_by_span(db, span_id)
    seg_responses = [SpanSegmentResponse.model_validate(s, from_attributes=True) for s in segments]
    return _build_span_response(span, seg_responses)


@router.get("/spans/{span_id}/attribution", response_model=AttributionResponse)
async def get_attribution(
    span_id: str,
    db: DbSession,
    org_id: OrgId,
    force: bool = Query(False, description="Force re-computation"),
) -> AttributionResponse:
    """Get attribution results for a span.

    Triggers segment detection and utilization scoring if not yet computed.
    Pass force=true to re-compute even if results exist.
    """
    result = await compute_attribution(db, span_id, org_id, force=force)

    return AttributionResponse(
        span_id=span_id,
        method=result.method,
        segments=[
            SpanSegmentResponse.model_validate(s, from_attributes=True) for s in result.segments
        ],
    )
