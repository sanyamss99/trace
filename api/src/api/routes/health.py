"""Health check endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from api.deps import DbSession

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe — always returns ok, does not touch the DB."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check(db: DbSession) -> dict[str, str]:
    """Readiness probe — verifies DB connectivity."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
