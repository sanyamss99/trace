"""Pydantic v2 model for trace span payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SpanData(BaseModel):
    """A single trace span matching the POST /ingest/batch schema."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    span_type: str = "generic"
    function_name: str = ""
    module: str = ""
    start_time: datetime = Field(default_factory=_utc_now)
    end_time: datetime | None = None
    duration_ms: float = 0.0
    status: str = "ok"
    error_type: str | None = None
    error_message: str | None = None

    # Capture data
    inputs: dict[str, Any] | None = None
    output: Any | None = None

    # LLM-specific fields
    model: str | None = None
    completion_text: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    completion_logprobs: list[float] | None = None

    # Metadata
    environment: str | None = None
    tags: dict[str, str] | None = None

    model_config = {"ser_json_timedelta": "float"}

    def estimated_bytes(self) -> int:
        """Estimate the serialized byte cost of this span for budget tracking.

        Uses field-length heuristics instead of full JSON serialization.
        Accurate to within ~15% — sufficient for approximate memory ceiling.
        """
        size = 350  # fixed: UUIDs, timestamps, field names, JSON punctuation
        if self.inputs:
            size += len(str(self.inputs))
        if self.output is not None:
            size += len(str(self.output))
        if self.completion_text:
            size += len(self.completion_text)
        if self.error_message:
            size += len(self.error_message)
        if self.tags:
            size += len(str(self.tags))
        return size
