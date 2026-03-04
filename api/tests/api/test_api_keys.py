"""Tests for API key management endpoints."""

from httpx import AsyncClient


async def test_create_api_key(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """POST /api-keys should create a new key and return the raw key once."""
    raw_key, _ = create_api_key
    response = await client.post(
        "/api-keys",
        json={"name": "my-new-key"},
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my-new-key"
    assert data["raw_key"].startswith("tr_")
    assert "id" in data


async def test_list_api_keys(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /api-keys should return all keys for the org."""
    raw_key, _ = create_api_key
    response = await client.get("/api-keys", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    # The fixture key should be in the list
    assert len(data) >= 1
    assert data[0]["revoked_at"] is None


async def test_revoke_api_key(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """DELETE /api-keys/:id should set revoked_at."""
    raw_key, _ = create_api_key

    # Create a new key to revoke (don't revoke the one we're using for auth)
    create_resp = await client.post(
        "/api-keys",
        json={"name": "to-revoke"},
        headers={"X-Trace-Key": raw_key},
    )
    key_id = create_resp.json()["id"]

    response = await client.delete(f"/api-keys/{key_id}", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200
    assert response.json()["revoked_at"] is not None


async def test_revoke_nonexistent_key(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """DELETE /api-keys/:id for missing key should return 404."""
    raw_key, _ = create_api_key
    response = await client.delete("/api-keys/nonexistent", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 404


async def test_created_key_works_for_auth(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """A newly created API key should authenticate successfully."""
    raw_key, _ = create_api_key

    # Create a new key
    create_resp = await client.post(
        "/api-keys",
        json={"name": "usable-key"},
        headers={"X-Trace-Key": raw_key},
    )
    new_key = create_resp.json()["raw_key"]

    # Use it to list traces
    response = await client.get("/traces", headers={"X-Trace-Key": new_key})
    assert response.status_code == 200


async def test_re_revoke_key_returns_409(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Revoking an already-revoked key should return 409."""
    raw_key, _ = create_api_key

    create_resp = await client.post(
        "/api-keys",
        json={"name": "double-revoke"},
        headers={"X-Trace-Key": raw_key},
    )
    key_id = create_resp.json()["id"]

    # First revoke: 200
    response = await client.delete(f"/api-keys/{key_id}", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200

    # Second revoke: 409
    response = await client.delete(f"/api-keys/{key_id}", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 409


async def test_cross_org_key_revoke_rejected(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    create_second_api_key: tuple[str, str],
) -> None:
    """Org A should not be able to revoke Org B's key."""
    key_a, _ = create_api_key
    key_b, _ = create_second_api_key

    # Create a key under Org B
    create_resp = await client.post(
        "/api-keys",
        json={"name": "org-b-key"},
        headers={"X-Trace-Key": key_b},
    )
    org_b_key_id = create_resp.json()["id"]

    # Org A tries to revoke Org B's key — should get 404 (scoped to org)
    response = await client.delete(
        f"/api-keys/{org_b_key_id}",
        headers={"X-Trace-Key": key_a},
    )
    assert response.status_code == 404
