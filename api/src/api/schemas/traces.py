"""Request/response schemas for trace and span read endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SpanSegmentResponse(BaseModel):
    """Single segment in API responses."""

    id: str
    segment_name: str
    segment_type: str
    segment_text: str
    position_start: int | None
    position_end: int | None
    retrieval_rank: int | None
    influence_score: float | None
    utilization_score: float | None
    attribution_method: str | None

    model_config = {"from_attributes": True}


class SpanResponse(BaseModel):
    """Single span in API responses."""

    id: str
    trace_id: str
    parent_span_id: str | None
    function_name: str
    span_type: str
    model: str | None
    started_at: datetime
    ended_at: datetime
    duration_ms: int | None
    prompt_text: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    completion_text: str | None
    completion_logprobs: list[dict[str, Any]] | None
    cost_usd: float | None
    input_locals: dict[str, Any] | None
    output: Any | None
    error: str | None
    metadata: dict[str, Any] | None = Field(validation_alias="span_metadata")
    segments: list[SpanSegmentResponse] = []

    model_config = {"from_attributes": True}


class AttributionResponse(BaseModel):
    """Response from GET /spans/:id/attribution."""

    span_id: str
    method: str
    segments: list[SpanSegmentResponse]


class TraceListItem(BaseModel):
    """Summary trace for list views (no nested spans)."""

    id: str
    function_name: str
    environment: str
    started_at: datetime
    ended_at: datetime
    duration_ms: int | None
    total_tokens: int | None
    total_cost_usd: float | None
    status: str
    tags: dict[str, Any] | None
    span_count: int

    model_config = {"from_attributes": True}


class PaginatedTraceListResponse(BaseModel):
    """Cursor-paginated list of traces."""

    traces: list[TraceListItem]
    next_cursor: str | None
    limit: int


class TraceDetailResponse(BaseModel):
    """Full trace with all spans."""

    id: str
    function_name: str
    environment: str
    started_at: datetime
    ended_at: datetime
    duration_ms: int | None
    total_tokens: int | None
    total_cost_usd: float | None
    status: str
    tags: dict[str, Any] | None
    spans: list[SpanResponse]

    model_config = {"from_attributes": True}


class FunctionCostItem(BaseModel):
    """Cost and usage aggregates for a single function."""

    function_name: str
    call_count: int
    total_tokens: int | None
    total_cost_usd: float | None
    avg_cost_usd: float | None
    avg_duration_ms: float | None
    error_count: int
    avg_quality_score: float | None = None


class ModelCostItem(BaseModel):
    """Cost and usage aggregates for a single model."""

    model: str
    call_count: int
    total_tokens: int | None
    total_cost_usd: float | None
    avg_cost_usd: float | None
    avg_quality_score: float | None = None


class LatencyPercentiles(BaseModel):
    """Latency percentile values in milliseconds."""

    p50: float | None
    p90: float | None
    p99: float | None


class FunctionDetailResponse(BaseModel):
    """Latency percentiles and recent call statuses for a single function."""

    function_name: str
    percentiles: LatencyPercentiles
    recent_statuses: list[str]


class OverviewStatsResponse(BaseModel):
    """Dashboard header summary stats."""

    trace_count: int
    total_tokens: int | None
    total_cost_usd: float | None
    avg_duration_ms: float | None
    error_count: int
    error_rate: float


class TimeSeriesPoint(BaseModel):
    """Single data point in a time-series."""

    date: str
    trace_count: int
    total_cost_usd: float | None
    error_count: int
