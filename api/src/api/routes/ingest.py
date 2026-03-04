"""Span ingestion endpoint — receives batches from the SDK."""

from fastapi import APIRouter

from api.deps import DbSession, OrgId
from api.exceptions import TraceAppError
from api.schemas.ingest import MAX_BATCH_SIZE, BatchIngestResponse, SpanIngestPayload
from api.services.ingest import process_batch

router = APIRouter()


class BatchTooLargeError(TraceAppError):
    """Raised when a batch exceeds the maximum allowed size."""

    def __init__(self, size: int) -> None:
        super().__init__(
            f"Batch size {size} exceeds maximum of {MAX_BATCH_SIZE}",
            status_code=413,
        )


@router.post("/ingest/batch", response_model=BatchIngestResponse)
async def ingest_batch(
    spans: list[SpanIngestPayload],
    db: DbSession,
    org_id: OrgId,
) -> BatchIngestResponse:
    """Accept a batch of spans from the SDK.

    Requires a valid X-Trace-Key header. Validates each span,
    groups by trace_id, upserts traces, and inserts spans.
    """
    if len(spans) > MAX_BATCH_SIZE:
        raise BatchTooLargeError(len(spans))

    result = await process_batch(db, spans, org_id)
    return BatchIngestResponse(
        accepted=result.accepted,
        failed=result.failed,
    )
