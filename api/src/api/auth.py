"""JWT token utilities for dashboard authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from api.config import settings

_ALGORITHM = "HS256"
_TOKEN_LIFETIME = timedelta(hours=24)


def create_access_token(user_id: str, org_id: str, email: str) -> str:
    """Create a signed JWT with user identity claims."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "email": email,
        "iat": now,
        "exp": now + _TOKEN_LIFETIME,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT.

    Raises jwt.ExpiredSignatureError if the token has expired.
    Raises jwt.InvalidTokenError for any other validation failure.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
