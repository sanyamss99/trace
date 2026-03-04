"""Request/response schemas for API key management."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateApiKeyRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(min_length=1, max_length=256)


class ApiKeyResponse(BaseModel):
    """API key metadata (never includes the raw key after creation)."""

    id: str
    name: str | None
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(BaseModel):
    """Response after creating a new API key — includes the raw key once."""

    id: str
    name: str | None
    raw_key: str
    created_at: datetime
