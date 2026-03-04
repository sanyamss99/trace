"""FastAPI dependencies — auth, DB session, etc."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import get_db
from api.exceptions import AuthenticationError, RateLimitError
from api.logger import logger
from api.models import ApiKey, _naive_utcnow
from api.rate_limit import auth_rate_limiter, org_rate_limiter

DbSession = Annotated[AsyncSession, Depends(get_db)]


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Authenticated caller identity."""

    org_id: str
    user_id: str


def _get_client_ip(request: Request) -> str:
    """Extract client IP, only trusting X-Forwarded-For when configured."""
    if settings.trust_proxy_headers:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _authenticate(
    request: Request,
    db: DbSession,
    x_trace_key: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Validate the X-Trace-Key header and return the full auth context.

    Raises AuthenticationError if the key is missing, unknown, or revoked.
    Raises RateLimitError if the client IP has too many recent failures.
    """
    client_ip = _get_client_ip(request)
    endpoint = request.url.path

    if await auth_rate_limiter.is_blocked(client_ip):
        logger.warning("Auth rate-limited ip=%s endpoint=%s", client_ip, endpoint)
        raise RateLimitError()

    if not x_trace_key:
        logger.warning("Auth failed: missing API key ip=%s endpoint=%s", client_ip, endpoint)
        await auth_rate_limiter.record_failure(client_ip)
        raise AuthenticationError("Missing X-Trace-Key header")

    key_prefix = x_trace_key[:8]
    key_hash = hashlib.sha256(x_trace_key.encode()).hexdigest()

    result = await db.execute(
        select(ApiKey.org_id, ApiKey.id, ApiKey.created_by).where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None),
        )
    )
    row = result.first()
    if not row:
        logger.warning(
            "Auth failed: invalid key key_prefix=%s ip=%s endpoint=%s",
            key_prefix,
            client_ip,
            endpoint,
        )
        await auth_rate_limiter.record_failure(client_ip)
        raise AuthenticationError()

    logger.info(
        "Auth success key_prefix=%s org_id=%s endpoint=%s",
        key_prefix,
        row.org_id,
        endpoint,
    )

    if await org_rate_limiter.check_and_record(row.org_id):
        logger.warning("Org rate-limited org_id=%s endpoint=%s", row.org_id, endpoint)
        raise RateLimitError()

    await db.execute(update(ApiKey).where(ApiKey.id == row.id).values(last_used_at=_naive_utcnow()))

    return AuthContext(org_id=row.org_id, user_id=row.created_by)


async def verify_api_key(
    request: Request,
    db: DbSession,
    x_trace_key: Annotated[str | None, Header()] = None,
) -> str:
    """Validate the X-Trace-Key header and return the org_id."""
    ctx = await _authenticate(request, db, x_trace_key)
    return ctx.org_id


async def get_auth_context(
    request: Request,
    db: DbSession,
    x_trace_key: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Validate the X-Trace-Key header and return the full auth context."""
    return await _authenticate(request, db, x_trace_key)


OrgId = Annotated[str, Depends(verify_api_key)]
Auth = Annotated[AuthContext, Depends(get_auth_context)]
