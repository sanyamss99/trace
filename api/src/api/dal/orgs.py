"""Data access layer for organization management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from api.models import JoinRequest, Organization, OrgMember, User, _naive_utcnow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def search_orgs(db: AsyncSession, query: str) -> list[Organization]:
    """Search organizations by name (case-insensitive)."""
    result = await db.execute(
        select(Organization).where(Organization.name.ilike(f"%{query}%")).limit(20)
    )
    return list(result.scalars().all())


async def get_org_by_id(db: AsyncSession, org_id: str) -> Organization | None:
    """Fetch an organization by ID."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    return result.scalar_one_or_none()


async def get_user_membership(db: AsyncSession, user_id: str) -> OrgMember | None:
    """Find a user's single org membership."""
    result = await db.execute(select(OrgMember).where(OrgMember.user_id == user_id))
    return result.scalar_one_or_none()


async def get_org_members(db: AsyncSession, org_id: str) -> list[OrgMember]:
    """List all members of an organization with eagerly loaded User."""
    result = await db.execute(
        select(OrgMember).options(joinedload(OrgMember.user)).where(OrgMember.org_id == org_id)
    )
    return list(result.scalars().all())


async def update_member_role(
    db: AsyncSession, org_id: str, user_id: str, role: str
) -> OrgMember | None:
    """Update a member's role. Returns None if member not found."""
    result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member:
        member.role = role
        await db.flush()
    return member


async def remove_member(db: AsyncSession, org_id: str, user_id: str) -> bool:
    """Remove a member from an organization. Returns True if removed."""
    result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member:
        await db.delete(member)
        await db.flush()
        return True
    return False


async def create_join_request(db: AsyncSession, org_id: str, user_id: str) -> JoinRequest:
    """Create a pending join request."""
    request = JoinRequest(org_id=org_id, user_id=user_id, status="pending")
    db.add(request)
    await db.flush()
    return request


async def get_pending_join_requests(db: AsyncSession, org_id: str) -> list[JoinRequest]:
    """List pending join requests for an org with eagerly loaded User."""
    result = await db.execute(
        select(JoinRequest)
        .options(joinedload(JoinRequest.user))
        .where(JoinRequest.org_id == org_id, JoinRequest.status == "pending")
    )
    return list(result.scalars().all())


async def get_pending_request_for_user(
    db: AsyncSession, org_id: str, user_id: str
) -> JoinRequest | None:
    """Check if a user already has a pending request for an org."""
    result = await db.execute(
        select(JoinRequest).where(
            JoinRequest.org_id == org_id,
            JoinRequest.user_id == user_id,
            JoinRequest.status == "pending",
        )
    )
    return result.scalar_one_or_none()


async def get_join_request_by_id(db: AsyncSession, request_id: str) -> JoinRequest | None:
    """Fetch a join request by ID with eagerly loaded User."""
    result = await db.execute(
        select(JoinRequest)
        .options(joinedload(JoinRequest.user))
        .where(JoinRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def resolve_join_request(
    db: AsyncSession,
    request_id: str,
    status: str,
    resolved_by: str,
) -> JoinRequest | None:
    """Update a join request's status to accepted or declined."""
    result = await db.execute(select(JoinRequest).where(JoinRequest.id == request_id))
    request = result.scalar_one_or_none()
    if request:
        request.status = status
        request.resolved_at = _naive_utcnow()
        request.resolved_by = resolved_by
        await db.flush()
    return request


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Fetch a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
