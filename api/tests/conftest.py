"""Shared test fixtures."""

import hashlib
import os
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.database import get_db
from api.main import app
from api.models import ApiKey, Base, Organization, User
from api.rate_limit import auth_rate_limiter, org_rate_limiter

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://localhost:5432/trace_test",
)


@pytest.fixture(autouse=True)
async def _reset_global_limiter() -> None:
    """Reset all global rate limiters before each test."""
    await auth_rate_limiter.reset()
    await org_rate_limiter.reset()


@pytest.fixture
async def db_engine():
    """Create a Postgres test engine, recreating all tables per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session from the shared engine."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Async test client that shares the test DB engine."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def create_org(db_session: AsyncSession) -> Organization:
    """Create and return a test organization."""
    org = Organization(name="Test Org")
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def create_api_key(db_session: AsyncSession, create_org: Organization) -> tuple[str, str]:
    """Create an API key and return (raw_key, org_id).

    The raw key is a random string. The DB stores its SHA-256 hash.
    """
    raw_key = f"tr_test_{uuid4().hex}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    user = User(email="test@example.com")
    db_session.add(user)
    await db_session.flush()

    api_key = ApiKey(
        org_id=create_org.id,
        created_by=user.id,
        key_hash=key_hash,
        name="test-key",
    )
    db_session.add(api_key)
    await db_session.commit()

    return raw_key, create_org.id


@pytest.fixture
async def create_second_api_key(db_session: AsyncSession) -> tuple[str, str]:
    """Create a second org + API key for isolation tests.

    Returns (raw_key, org_id) for the second organization.
    """
    org = Organization(name="Other Org")
    db_session.add(org)
    await db_session.flush()

    user = User(email="other@example.com")
    db_session.add(user)
    await db_session.flush()

    raw_key = f"tr_test_{uuid4().hex}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        org_id=org.id,
        created_by=user.id,
        key_hash=key_hash,
        name="other-key",
    )
    db_session.add(api_key)
    await db_session.commit()

    return raw_key, org.id
