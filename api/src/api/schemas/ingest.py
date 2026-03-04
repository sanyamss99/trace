"""Request/response schemas for the /ingest/batch endpoint."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from api.constants import STATUS_OK

# Maximum number of spans in a single batch request.
MAX_BATCH_SIZE = 1000

# Per-field size rationale (derived from SDK field analysis):
#   completion_text: LLM responses up to ~200KB; 1MB gives 5x headroom.
#   error_message: Deep stack traces can reach ~50KB; 100KB gives 2x headroom.
#   completion_logprobs: ~10K entries for a 10K-token response; 100K gives 10x.
#   inputs/output: SDK truncates strings via max_string_length (~10KB default),
#       but nested dicts can be larger. 512KB covers realistic payloads.
#   tags: Typically 1-10KB of flat key-value pairs. 64KB is generous.
_MAX_JSON_BYTES_INPUTS = 512_000  # 512 KB
_MAX_JSON_BYTES_OUTPUT = 512_000  # 512 KB
_MAX_JSON_BYTES_TAGS = 64_000  # 64 KB


class SpanIngestPayload(BaseModel):
    """Validates a single span from the SDK's SpanData.model_dump(mode='json').

    Field names match the SDK contract exactly.
    """

    trace_id: str = Field(max_length=64)
    span_id: str = Field(max_length=64)
    parent_span_id: str | None = Field(None, max_length=64)
    span_type: str = Field("generic", max_length=64)
    function_name: str = Field("", max_length=512)
    module: str = Field("", max_length=512)
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float = 0.0
    status: str = Field(STATUS_OK, max_length=32)
    error_type: str | None = Field(None, max_length=256)
    error_message: str | None = Field(None, max_length=100_000)
    inputs: dict[str, Any] | None = None
    output: Any | None = None
    model: str | None = Field(None, max_length=256)
    prompt_text: str | None = Field(None, max_length=1_000_000)
    completion_text: str | None = Field(None, max_length=1_000_000)
    prompt_tokens: int | None = Field(None, ge=0, le=10_000_000)
    completion_tokens: int | None = Field(None, ge=0, le=10_000_000)
    completion_logprobs: list[dict[str, Any]] | None = Field(None, max_length=10_000_000)
    environment: str | None = Field(None, max_length=128)
    tags: dict[str, str] | None = None

    @field_validator("inputs")
    @classmethod
    def check_inputs_size(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Reject inputs dicts that exceed the byte budget."""
        if v is not None and len(json.dumps(v, default=str)) > _MAX_JSON_BYTES_INPUTS:
            msg = f"inputs exceeds {_MAX_JSON_BYTES_INPUTS} bytes when serialized"
            raise ValueError(msg)
        return v

    @field_validator("output")
    @classmethod
    def check_output_size(cls, v: Any | None) -> Any | None:
        """Reject output values that exceed the byte budget."""
        if v is not None and len(json.dumps(v, default=str)) > _MAX_JSON_BYTES_OUTPUT:
            msg = f"output exceeds {_MAX_JSON_BYTES_OUTPUT} bytes when serialized"
            raise ValueError(msg)
        return v

    @field_validator("tags")
    @classmethod
    def check_tags_size(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Reject tags dicts that exceed the byte budget."""
        if v is not None and len(json.dumps(v)) > _MAX_JSON_BYTES_TAGS:
            msg = f"tags exceeds {_MAX_JSON_BYTES_TAGS} bytes when serialized"
            raise ValueError(msg)
        return v

    model_config = {"extra": "ignore"}


class BatchIngestResponse(BaseModel):
    """Response from POST /ingest/batch."""

    status: str = STATUS_OK
    accepted: int
    failed: int = 0
