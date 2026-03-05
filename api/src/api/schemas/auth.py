"""Request/response schemas for authentication."""

from pydantic import BaseModel


class AuthUserResponse(BaseModel):
    """Current authenticated user info."""

    user_id: str
    org_id: str
    email: str
