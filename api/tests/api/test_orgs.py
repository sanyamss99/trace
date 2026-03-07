"""Tests for organization management endpoints."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import create_access_token
from api.models import JoinRequest, Organization, OrgMember, User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db: AsyncSession, email: str) -> User:
    user = User(email=email)
    db.add(user)
    await db.flush()
    return user


async def _create_org_with_owner(
    db: AsyncSession, org_name: str, owner_email: str
) -> tuple[Organization, User]:
    org = Organization(name=org_name)
    db.add(org)
    await db.flush()
    user = await _create_user(db, owner_email)
    member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
    db.add(member)
    await db.flush()
    return org, user


def _jwt(user_id: str, org_id: str, email: str) -> dict[str, str]:
    token = create_access_token(user_id, org_id, email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /orgs — create org
# ---------------------------------------------------------------------------


async def test_create_org(client: AsyncClient, db_session: AsyncSession) -> None:
    """A user without an org can create one and become owner."""
    user = await _create_user(db_session, "alice@example.com")
    await db_session.commit()

    resp = await client.post(
        "/orgs",
        json={"name": "Alice's Team"},
        headers=_jwt(user.id, "", "alice@example.com"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Alice's Team"
    assert data["id"]


async def test_create_org_conflict(client: AsyncClient, db_session: AsyncSession) -> None:
    """A user already in an org cannot create another."""
    org, user = await _create_org_with_owner(db_session, "Existing", "bob@example.com")
    await db_session.commit()

    resp = await client.post(
        "/orgs",
        json={"name": "Second Org"},
        headers=_jwt(user.id, org.id, "bob@example.com"),
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /orgs/search
# ---------------------------------------------------------------------------


async def test_search_orgs(client: AsyncClient, db_session: AsyncSession) -> None:
    """Search returns matching organizations."""
    org, _ = await _create_org_with_owner(db_session, "Acme Corp", "owner@acme.com")
    user = await _create_user(db_session, "searcher@example.com")
    await db_session.commit()

    resp = await client.get(
        "/orgs/search?q=Acme",
        headers=_jwt(user.id, "", "searcher@example.com"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["orgs"]) == 1
    assert data["orgs"][0]["name"] == "Acme Corp"


async def test_search_orgs_no_match(client: AsyncClient, db_session: AsyncSession) -> None:
    """Search with no match returns empty list."""
    user = await _create_user(db_session, "searcher@example.com")
    await db_session.commit()

    resp = await client.get(
        "/orgs/search?q=nonexistent",
        headers=_jwt(user.id, "", "searcher@example.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["orgs"] == []


# ---------------------------------------------------------------------------
# GET /orgs/current
# ---------------------------------------------------------------------------


async def test_get_current_org(client: AsyncClient, db_session: AsyncSession) -> None:
    """Returns the user's current org."""
    org, user = await _create_org_with_owner(db_session, "My Team", "me@example.com")
    await db_session.commit()

    resp = await client.get(
        "/orgs/current",
        headers=_jwt(user.id, org.id, "me@example.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Team"


async def test_get_current_org_no_org(client: AsyncClient, db_session: AsyncSession) -> None:
    """Returns 404 when user has no org."""
    user = await _create_user(db_session, "orphan@example.com")
    await db_session.commit()

    resp = await client.get(
        "/orgs/current",
        headers=_jwt(user.id, "", "orphan@example.com"),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /orgs/current/refresh-token
# ---------------------------------------------------------------------------


async def test_refresh_token(client: AsyncClient, db_session: AsyncSession) -> None:
    """Refresh token returns a new JWT with current org_id."""
    org, user = await _create_org_with_owner(db_session, "Team", "user@example.com")
    await db_session.commit()

    resp = await client.post(
        "/orgs/current/refresh-token",
        headers=_jwt(user.id, "", "user@example.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["token"]


# ---------------------------------------------------------------------------
# GET /orgs/current/members
# ---------------------------------------------------------------------------


async def test_list_members(client: AsyncClient, db_session: AsyncSession) -> None:
    """Owner can list org members."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    member_user = await _create_user(db_session, "member@example.com")
    db_session.add(OrgMember(org_id=org.id, user_id=member_user.id, role="member"))
    await db_session.commit()

    resp = await client.get(
        "/orgs/current/members",
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 200
    members = resp.json()["members"]
    assert len(members) == 2


async def test_list_members_non_owner(client: AsyncClient, db_session: AsyncSession) -> None:
    """Non-owner cannot list members."""
    org, _ = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    member_user = await _create_user(db_session, "member@example.com")
    db_session.add(OrgMember(org_id=org.id, user_id=member_user.id, role="member"))
    await db_session.commit()

    resp = await client.get(
        "/orgs/current/members",
        headers=_jwt(member_user.id, org.id, "member@example.com"),
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /orgs/current/members/{user_id}
# ---------------------------------------------------------------------------


async def test_update_member_role(client: AsyncClient, db_session: AsyncSession) -> None:
    """Owner can promote a member to owner."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    member_user = await _create_user(db_session, "member@example.com")
    db_session.add(OrgMember(org_id=org.id, user_id=member_user.id, role="member"))
    await db_session.commit()

    resp = await client.patch(
        f"/orgs/current/members/{member_user.id}",
        json={"role": "owner"},
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"


# ---------------------------------------------------------------------------
# DELETE /orgs/current/members/{user_id}
# ---------------------------------------------------------------------------


async def test_remove_member(client: AsyncClient, db_session: AsyncSession) -> None:
    """Owner can remove a member."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    member_user = await _create_user(db_session, "member@example.com")
    db_session.add(OrgMember(org_id=org.id, user_id=member_user.id, role="member"))
    await db_session.commit()

    resp = await client.delete(
        f"/orgs/current/members/{member_user.id}",
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 204


async def test_cannot_remove_self(client: AsyncClient, db_session: AsyncSession) -> None:
    """Owner cannot remove themselves."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    await db_session.commit()

    resp = await client.delete(
        f"/orgs/current/members/{owner.id}",
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /orgs/{org_id}/join
# ---------------------------------------------------------------------------


async def test_request_to_join(client: AsyncClient, db_session: AsyncSession) -> None:
    """A user without an org can request to join one."""
    org, _ = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    requester = await _create_user(db_session, "requester@example.com")
    await db_session.commit()

    resp = await client.post(
        f"/orgs/{org.id}/join",
        headers=_jwt(requester.id, "", "requester@example.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


async def test_request_to_join_already_in_org(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """User already in an org cannot request to join another."""
    org1, owner = await _create_org_with_owner(db_session, "Team 1", "owner@example.com")
    org2 = Organization(name="Team 2")
    db_session.add(org2)
    await db_session.commit()

    resp = await client.post(
        f"/orgs/{org2.id}/join",
        headers=_jwt(owner.id, org1.id, "owner@example.com"),
    )
    assert resp.status_code == 409


async def test_request_to_join_duplicate(client: AsyncClient, db_session: AsyncSession) -> None:
    """Duplicate pending request returns 409."""
    org, _ = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    requester = await _create_user(db_session, "requester@example.com")
    db_session.add(JoinRequest(org_id=org.id, user_id=requester.id, status="pending"))
    await db_session.commit()

    resp = await client.post(
        f"/orgs/{org.id}/join",
        headers=_jwt(requester.id, "", "requester@example.com"),
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /orgs/current/join-requests
# ---------------------------------------------------------------------------


async def test_list_join_requests(client: AsyncClient, db_session: AsyncSession) -> None:
    """Owner can list pending join requests."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    requester = await _create_user(db_session, "requester@example.com")
    db_session.add(JoinRequest(org_id=org.id, user_id=requester.id, status="pending"))
    await db_session.commit()

    resp = await client.get(
        "/orgs/current/join-requests",
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 200
    requests = resp.json()["requests"]
    assert len(requests) == 1
    assert requests[0]["user_email"] == "requester@example.com"


# ---------------------------------------------------------------------------
# POST /orgs/current/join-requests/{request_id} — accept/decline
# ---------------------------------------------------------------------------


async def test_accept_join_request(client: AsyncClient, db_session: AsyncSession) -> None:
    """Accepting a join request creates membership."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    requester = await _create_user(db_session, "requester@example.com")
    jr = JoinRequest(org_id=org.id, user_id=requester.id, status="pending")
    db_session.add(jr)
    await db_session.commit()

    resp = await client.post(
        f"/orgs/current/join-requests/{jr.id}",
        json={"action": "accept"},
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


async def test_decline_join_request(client: AsyncClient, db_session: AsyncSession) -> None:
    """Declining a join request does not create membership."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    requester = await _create_user(db_session, "requester@example.com")
    jr = JoinRequest(org_id=org.id, user_id=requester.id, status="pending")
    db_session.add(jr)
    await db_session.commit()

    resp = await client.post(
        f"/orgs/current/join-requests/{jr.id}",
        json={"action": "decline"},
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "declined"


async def test_resolve_already_resolved(client: AsyncClient, db_session: AsyncSession) -> None:
    """Resolving an already-resolved request returns 409."""
    org, owner = await _create_org_with_owner(db_session, "Team", "owner@example.com")
    requester = await _create_user(db_session, "requester@example.com")
    jr = JoinRequest(org_id=org.id, user_id=requester.id, status="accepted")
    db_session.add(jr)
    await db_session.commit()

    resp = await client.post(
        f"/orgs/current/join-requests/{jr.id}",
        json={"action": "accept"},
        headers=_jwt(owner.id, org.id, "owner@example.com"),
    )
    assert resp.status_code == 409
