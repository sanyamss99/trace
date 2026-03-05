"""Data access layer for user/org provisioning during OAuth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from api.models import Organization, OrgMember, User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Look up a user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str) -> User:
    """Create a new user with the given email."""
    user = User(email=email)
    db.add(user)
    await db.flush()
    return user


async def get_single_org(db: AsyncSession) -> Organization | None:
    """Return the first organization (single-team mode)."""
    result = await db.execute(select(Organization).limit(1))
    return result.scalar_one_or_none()


async def create_org(db: AsyncSession, name: str) -> Organization:
    """Create a new organization."""
    org = Organization(name=name)
    db.add(org)
    await db.flush()
    return org


async def get_membership(db: AsyncSession, org_id: str, user_id: str) -> OrgMember | None:
    """Look up an org membership."""
    result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_membership(
    db: AsyncSession, org_id: str, user_id: str, role: str = "member"
) -> OrgMember:
    """Create an org membership for a user."""
    member = OrgMember(org_id=org_id, user_id=user_id, role=role)
    db.add(member)
    await db.flush()
    return member
