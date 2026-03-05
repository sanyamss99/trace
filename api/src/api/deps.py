"""FastAPI dependencies — auth, DB session, etc."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
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
    email: str = field(default="")


def _extract_bearer_token(request: Request) -> str | None:
    """Extract a Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def _authenticate_jwt(token: str) -> AuthContext:
    """Validate a JWT and return an AuthContext.

    Raises AuthenticationError on invalid/expired tokens.
    """
    import jwt

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as err:
        raise AuthenticationError("Token has expired") from err
    except jwt.InvalidTokenError as err:
        raise AuthenticationError("Invalid token") from err

    return AuthContext(
        org_id=payload["org_id"],
        user_id=payload["sub"],
        email=payload.get("email", ""),
    )


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
    """Validate credentials and return the auth context.

    Tries Bearer JWT first, then falls back to X-Trace-Key.
    Raises AuthenticationError if neither is provided or valid.
    Raises RateLimitError if the client IP has too many recent failures.
    """
    # Try JWT first
    bearer_token = _extract_bearer_token(request)
    if bearer_token:
        return _authenticate_jwt(bearer_token)

    # Fall back to API key
    client_ip = _get_client_ip(request)
    endpoint = request.url.path

    if await auth_rate_limiter.is_blocked(client_ip):
        logger.warning("Auth rate-limited ip=%s endpoint=%s", client_ip, endpoint)
        raise RateLimitError()

    if not x_trace_key:
        logger.warning("Auth failed: missing credentials ip=%s endpoint=%s", client_ip, endpoint)
        await auth_rate_limiter.record_failure(client_ip)
        raise AuthenticationError("Missing authentication credentials")

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
    """Validate credentials and return the full auth context."""
    return await _authenticate(request, db, x_trace_key)


async def get_jwt_auth(request: Request) -> AuthContext:
    """JWT-only authentication dependency (for endpoints like /auth/me)."""
    bearer_token = _extract_bearer_token(request)
    if not bearer_token:
        raise AuthenticationError("Missing Bearer token")
    return _authenticate_jwt(bearer_token)


OrgId = Annotated[str, Depends(verify_api_key)]
Auth = Annotated[AuthContext, Depends(get_auth_context)]
JwtAuth = Annotated[AuthContext, Depends(get_jwt_auth)]
