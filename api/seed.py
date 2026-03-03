"""Seed the local database with tables and a dev API key.

Usage:
    cd api && uv run python seed.py
"""

import asyncio
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings
from api.models import ApiKey, Base, Organization, OrgMember, User


async def seed() -> None:
    engine = create_async_engine(settings.database_url, echo=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        # Check if org already exists
        result = await db.execute(select(Organization).where(Organization.name == "Local Dev"))
        if result.scalar_one_or_none():
            print("Seed data already exists. Skipping.")
            await engine.dispose()
            return

        # Create org
        org = Organization(name="Local Dev", plan="hobby")
        db.add(org)
        await db.flush()

        # Create user
        user = User(email="dev@localhost")
        db.add(user)
        await db.flush()

        # Create membership
        member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
        db.add(member)
        await db.flush()

        # Create API key matching the test app's api_key="local-dev"
        raw_key = "local-dev"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = ApiKey(
            org_id=org.id,
            created_by=user.id,
            key_hash=key_hash,
            name="local-dev-key",
        )
        db.add(api_key)
        await db.commit()

        print(f"Org:     {org.id} ({org.name})")
        print(f"User:    {user.id} ({user.email})")
        print(f"API Key: raw='local-dev', hash={key_hash}")
        print("Seed complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
