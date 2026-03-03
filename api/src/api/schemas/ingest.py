"""Request/response schemas for the /ingest/batch endpoint."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SpanIngestPayload(BaseModel):
    """Validates a single span from the SDK's SpanData.model_dump(mode='json').

    Field names match the SDK contract exactly.
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    span_type: str = "generic"
    function_name: str = ""
    module: str = ""
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float = 0.0
    status: str = "ok"
    error_type: str | None = None
    error_message: str | None = None
    inputs: dict[str, Any] | None = None
    output: Any | None = None
    model: str | None = None
    completion_text: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    completion_logprobs: list[float] | None = None
    environment: str | None = None
    tags: dict[str, str] | None = None

    model_config = {"extra": "ignore"}


class BatchIngestResponse(BaseModel):
    """Response from POST /ingest/batch."""

    status: str = "ok"
    accepted: int
    failed: int = 0
