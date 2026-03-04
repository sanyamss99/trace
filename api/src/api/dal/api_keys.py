"""Data access layer for API key records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from api.models import ApiKey

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def list_api_keys(db: AsyncSession, org_id: str) -> list[ApiKey]:
    """List all API keys for an org, ordered by creation date."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.org_id == org_id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def get_api_key_by_id(
    db: AsyncSession,
    key_id: str,
    org_id: str,
) -> ApiKey | None:
    """Fetch a single API key by ID, scoped to org."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org_id))
    return result.scalar_one_or_none()


async def create_api_key(
    db: AsyncSession,
    *,
    org_id: str,
    created_by: str,
    key_hash: str,
    name: str,
) -> ApiKey:
    """Create a new API key."""
    key = ApiKey(
        org_id=org_id,
        created_by=created_by,
        key_hash=key_hash,
        name=name,
    )
    db.add(key)
    await db.flush()
    return key


async def revoke_api_key(
    db: AsyncSession,
    key_id: str,
    org_id: str,
) -> tuple[ApiKey | None, bool]:
    """Revoke an API key by setting revoked_at.

    Returns (None, False) if the key was not found, (key, True) if already
    revoked, or (key, False) on successful revocation.
    """
    key = await get_api_key_by_id(db, key_id, org_id)
    if key is None:
        return None, False
    if key.revoked_at is not None:
        return key, True
    key.revoked_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    return key, False
