"""FastAPI dependencies — auth, DB session, etc."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.exceptions import AuthenticationError
from api.models import ApiKey

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def verify_api_key(
    db: DbSession,
    x_trace_key: Annotated[str | None, Header()] = None,
) -> str:
    """Validate the X-Trace-Key header and return the org_id.

    Raises AuthenticationError if the key is missing, unknown, or revoked.
    """
    if not x_trace_key:
        raise AuthenticationError("Missing X-Trace-Key header")

    key_hash = hashlib.sha256(x_trace_key.encode()).hexdigest()

    result = await db.execute(
        select(ApiKey.org_id, ApiKey.id).where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None),
        )
    )
    row = result.first()
    if not row:
        raise AuthenticationError()

    await db.execute(
        update(ApiKey).where(ApiKey.id == row.id).values(last_used_at=datetime.now(UTC))
    )

    return row.org_id


OrgId = Annotated[str, Depends(verify_api_key)]
