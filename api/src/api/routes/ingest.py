"""Span ingestion endpoint — receives batches from the SDK."""

from typing import Any

from fastapi import APIRouter

from api.logger import logger

router = APIRouter()


@router.post("/ingest/batch")
async def ingest_batch(spans: list[dict[str, Any]]) -> dict[str, str]:
    """Accept a batch of spans from the SDK. Returns ok."""
    logger.info("Ingested %d spans", len(spans))
    return {"status": "ok"}
