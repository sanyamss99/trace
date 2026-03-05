"""Tests for Google OAuth and JWT authentication."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from httpx import AsyncClient

from api.auth import create_access_token, decode_access_token
from api.config import settings

# ---------------------------------------------------------------------------
# JWT round-trip
# ---------------------------------------------------------------------------


def test_jwt_round_trip() -> None:
    """A token created by create_access_token should be decodable."""
    token = create_access_token("user-1", "org-1", "user@example.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["org_id"] == "org-1"
    assert payload["email"] == "user@example.com"


def test_jwt_expired_token() -> None:
    """An expired token should raise ExpiredSignatureError."""
    past = datetime.now(UTC) - timedelta(hours=25)
    payload = {
        "sub": "user-1",
        "org_id": "org-1",
        "email": "user@example.com",
        "iat": past,
        "exp": past + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_jwt_invalid_token() -> None:
    """A token signed with the wrong secret should fail."""
    payload = {
        "sub": "user-1",
        "org_id": "org-1",
        "email": "user@example.com",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


# ---------------------------------------------------------------------------
# JWT works on existing endpoints (dual auth)
# ---------------------------------------------------------------------------


async def test_jwt_auth_on_existing_endpoint(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """A valid JWT should authenticate on endpoints that normally use API keys."""
    _, org_id = create_api_key
    token = create_access_token("user-1", org_id, "user@example.com")

    response = await client.get(
        "/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# API key backward compatibility
# ---------------------------------------------------------------------------


async def test_api_key_still_works(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """X-Trace-Key header should still work for authentication."""
    raw_key, _ = create_api_key
    response = await client.get(
        "/api-keys",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# No credentials → 401
# ---------------------------------------------------------------------------


async def test_no_credentials_returns_401(client: AsyncClient) -> None:
    """Requests without any credentials should get 401."""
    response = await client.get("/api-keys")
    assert response.status_code == 401


async def test_invalid_bearer_returns_401(client: AsyncClient) -> None:
    """An invalid Bearer token should get 401."""
    response = await client.get(
        "/api-keys",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Google login redirect
# ---------------------------------------------------------------------------


async def test_google_login_redirect(client: AsyncClient) -> None:
    """GET /auth/google should redirect to Google when configured."""
    with patch.object(settings, "google_client_id", "test-client-id"):
        response = await client.get("/auth/google", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert "accounts.google.com" in location
    assert "test-client-id" in location


async def test_google_login_unconfigured(client: AsyncClient) -> None:
    """GET /auth/google should return 401 when Google OAuth is not configured."""
    with patch.object(settings, "google_client_id", ""):
        response = await client.get("/auth/google")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------


async def test_auth_me_happy_path(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /auth/me should return user info for a valid JWT."""
    _, org_id = create_api_key
    token = create_access_token("user-1", org_id, "me@example.com")

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["user_id"] == "user-1"
    assert data["org_id"] == org_id


async def test_auth_me_no_token(client: AsyncClient) -> None:
    """GET /auth/me should return 401 without a token."""
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_auth_me_api_key_rejected(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /auth/me should reject API key auth (JWT only)."""
    raw_key, _ = create_api_key
    response = await client.get(
        "/auth/me",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 401
