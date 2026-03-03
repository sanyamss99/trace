"""Request/response schemas for trace and span read endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
    prompt_tokens: int | None
    completion_tokens: int | None
    completion_text: str | None
    completion_logprobs: list[Any] | None
    cost_usd: float | None
    input_locals: dict[str, Any] | None
    error: str | None
    metadata: dict[str, Any] | None = Field(validation_alias="span_metadata")

    model_config = {"from_attributes": True}


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
    """Paginated list of traces."""

    traces: list[TraceListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


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
