"""Tests for rate limiting and audit logging."""

import logging

import pytest
from httpx import AsyncClient

from api.rate_limit import AuthFailureRateLimiter, OrgRequestRateLimiter

# ---------------------------------------------------------------------------
# Unit tests for AuthFailureRateLimiter
# ---------------------------------------------------------------------------


@pytest.fixture
async def limiter() -> AuthFailureRateLimiter:
    """Create a fresh rate limiter for each test."""
    return AuthFailureRateLimiter(max_failures=3, window_seconds=60)


async def test_not_blocked_initially(limiter: AuthFailureRateLimiter) -> None:
    """A fresh IP should not be blocked."""
    assert await limiter.is_blocked("1.2.3.4") is False


async def test_blocked_after_max_failures(limiter: AuthFailureRateLimiter) -> None:
    """IP should be blocked after exceeding max_failures."""
    for _ in range(3):
        await limiter.record_failure("1.2.3.4")
    assert await limiter.is_blocked("1.2.3.4") is True


async def test_not_blocked_below_threshold(limiter: AuthFailureRateLimiter) -> None:
    """IP should not be blocked below the threshold."""
    for _ in range(2):
        await limiter.record_failure("1.2.3.4")
    assert await limiter.is_blocked("1.2.3.4") is False


async def test_different_ips_independent(limiter: AuthFailureRateLimiter) -> None:
    """Rate limiting should be independent per IP."""
    for _ in range(3):
        await limiter.record_failure("1.1.1.1")
    assert await limiter.is_blocked("1.1.1.1") is True
    assert await limiter.is_blocked("2.2.2.2") is False


async def test_reset_clears_all(limiter: AuthFailureRateLimiter) -> None:
    """reset() should unblock all IPs."""
    for _ in range(3):
        await limiter.record_failure("1.2.3.4")
    assert await limiter.is_blocked("1.2.3.4") is True
    await limiter.reset()
    assert await limiter.is_blocked("1.2.3.4") is False


# ---------------------------------------------------------------------------
# Integration tests via HTTP client
# ---------------------------------------------------------------------------


async def test_rate_limit_blocks_after_threshold(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """After 10 failed auth attempts, the 11th should get 429."""
    for i in range(10):
        response = await client.post(
            "/ingest/batch",
            json=[],
            headers={"X-Trace-Key": f"tr_bad_key_{i}"},
        )
        assert response.status_code == 401

    response = await client.post(
        "/ingest/batch",
        json=[],
        headers={"X-Trace-Key": "tr_bad_key_final"},
    )
    assert response.status_code == 429


async def test_rate_limit_does_not_block_successful_auth(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Successful auth should always work, even after some failures."""
    raw_key, _ = create_api_key
    for i in range(5):
        await client.post(
            "/ingest/batch",
            json=[],
            headers={"X-Trace-Key": f"tr_bad_key_{i}"},
        )

    response = await client.get("/traces", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Audit logging tests
# ---------------------------------------------------------------------------


async def test_auth_success_logged(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Successful auth should log at INFO with key prefix and org_id."""
    raw_key, org_id = create_api_key
    with caplog.at_level(logging.INFO, logger="trace"):
        await client.get("/traces", headers={"X-Trace-Key": raw_key})
    assert "Auth success" in caplog.text
    assert raw_key[:8] in caplog.text
    assert org_id in caplog.text


async def test_auth_failure_logged(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failed auth should log at WARNING with key prefix."""
    with caplog.at_level(logging.WARNING, logger="trace"):
        await client.post(
            "/ingest/batch",
            json=[],
            headers={"X-Trace-Key": "tr_bogus_key_1234"},
        )
    assert "Auth failed" in caplog.text
    assert "tr_bogus" in caplog.text


# ---------------------------------------------------------------------------
# Unit tests for OrgRequestRateLimiter
# ---------------------------------------------------------------------------


@pytest.fixture
async def org_limiter() -> OrgRequestRateLimiter:
    """Create a fresh per-org rate limiter for each test."""
    return OrgRequestRateLimiter(max_requests=5, window_seconds=60)


async def test_org_not_limited_initially(org_limiter: OrgRequestRateLimiter) -> None:
    """First request should not be limited."""
    assert await org_limiter.check_and_record("org-1") is False


async def test_org_limited_after_max_requests(org_limiter: OrgRequestRateLimiter) -> None:
    """Org should be limited after exceeding max_requests."""
    for _ in range(5):
        await org_limiter.check_and_record("org-1")
    assert await org_limiter.check_and_record("org-1") is True


async def test_org_different_orgs_independent(org_limiter: OrgRequestRateLimiter) -> None:
    """Rate limiting should be independent per org."""
    for _ in range(5):
        await org_limiter.check_and_record("org-1")
    assert await org_limiter.check_and_record("org-1") is True
    assert await org_limiter.check_and_record("org-2") is False


async def test_org_reset_clears_all(org_limiter: OrgRequestRateLimiter) -> None:
    """reset() should unblock all orgs."""
    for _ in range(5):
        await org_limiter.check_and_record("org-1")
    assert await org_limiter.check_and_record("org-1") is True
    await org_limiter.reset()
    assert await org_limiter.check_and_record("org-1") is False
