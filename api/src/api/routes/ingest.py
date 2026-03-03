"""Span ingestion endpoint — receives batches from the SDK."""

from fastapi import APIRouter

from api.deps import DbSession, OrgId
from api.schemas.ingest import BatchIngestResponse, SpanIngestPayload
from api.services.ingest import process_batch

router = APIRouter()


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
    result = await process_batch(db, spans, org_id)
    return BatchIngestResponse(
        accepted=result.accepted,
        failed=result.failed,
    )
