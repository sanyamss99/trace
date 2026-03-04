"""Tests for health check endpoints."""

import uuid

from httpx import AsyncClient


async def test_health_liveness(client: AsyncClient) -> None:
    """Liveness probe should return ok without touching the DB."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_readiness(client: AsyncClient) -> None:
    """Readiness probe should verify DB connectivity and return ok."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_request_id_generated(client: AsyncClient) -> None:
    """Response should include an auto-generated X-Request-ID header."""
    response = await client.get("/health")
    rid = response.headers.get("x-request-id")
    assert rid is not None
    # Should be a valid UUID
    uuid.UUID(rid)


async def test_request_id_passthrough(client: AsyncClient) -> None:
    """If the client sends X-Request-ID, it should be echoed back."""
    custom_id = "my-correlation-id-123"
    response = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("x-request-id") == custom_id
