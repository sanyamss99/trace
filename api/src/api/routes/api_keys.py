"""API key management endpoints."""

import hashlib
import secrets

from fastapi import APIRouter

from api.dal import api_keys as api_key_dal
from api.deps import Auth, DbSession
from api.exceptions import ConflictError, NotFoundError
from api.schemas.api_keys import ApiKeyCreatedResponse, ApiKeyResponse, CreateApiKeyRequest

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _generate_raw_key() -> str:
    """Generate a cryptographically random API key."""
    return f"tr_{secrets.token_hex(24)}"


@router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    db: DbSession,
    auth: Auth,
) -> ApiKeyCreatedResponse:
    """Create a new API key for the authenticated organization.

    The raw key is returned only once in this response.
    """
    raw_key = _generate_raw_key()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    key = await api_key_dal.create_api_key(
        db,
        org_id=auth.org_id,
        created_by=auth.user_id,
        key_hash=key_hash,
        name=body.name,
    )

    return ApiKeyCreatedResponse(
        id=key.id,
        name=key.name,
        raw_key=raw_key,
        created_at=key.created_at,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: DbSession,
    auth: Auth,
) -> list[ApiKeyResponse]:
    """List all API keys for the authenticated organization."""
    keys = await api_key_dal.list_api_keys(db, auth.org_id)
    return [ApiKeyResponse.model_validate(k, from_attributes=True) for k in keys]


@router.delete("/{key_id}", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: str,
    db: DbSession,
    auth: Auth,
) -> ApiKeyResponse:
    """Revoke an API key (soft delete via revoked_at timestamp)."""
    key, already_revoked = await api_key_dal.revoke_api_key(db, key_id, auth.org_id)
    if key is None:
        raise NotFoundError("ApiKey", key_id)
    if already_revoked:
        raise ConflictError("API key is already revoked")
    return ApiKeyResponse.model_validate(key, from_attributes=True)
