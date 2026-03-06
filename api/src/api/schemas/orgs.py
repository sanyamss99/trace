"""Request/response schemas for organization management."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class OrgCreateRequest(BaseModel):
    """Request body for creating an organization."""

    name: str


class OrgResponse(BaseModel):
    """Organization info."""

    id: str
    name: str
    plan: str
    created_at: datetime


class OrgSearchResponse(BaseModel):
    """List of organizations from search."""

    orgs: list[OrgResponse]


class MemberResponse(BaseModel):
    """Organization member info."""

    user_id: str
    email: str
    role: str
    joined_at: datetime


class MembersListResponse(BaseModel):
    """List of organization members."""

    members: list[MemberResponse]


class JoinRequestResponse(BaseModel):
    """Join request info."""

    id: str
    user_id: str
    user_email: str
    status: str
    created_at: datetime


class JoinRequestsListResponse(BaseModel):
    """List of join requests."""

    requests: list[JoinRequestResponse]


class JoinRequestAction(BaseModel):
    """Action to take on a join request."""

    action: Literal["accept", "decline"]


class RoleUpdateRequest(BaseModel):
    """Request body for updating a member's role."""

    role: Literal["owner", "member"]


class TokenResponse(BaseModel):
    """Response containing a JWT token."""

    token: str
