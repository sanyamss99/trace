"""Organization management endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.auth import create_access_token
from api.dal import auth as auth_dal
from api.dal import orgs as orgs_dal
from api.deps import DbSession, JwtAuth  # noqa: TCH001
from api.exceptions import AuthenticationError, ConflictError, NotFoundError
from api.logger import logger
from api.schemas.orgs import (
    JoinRequestAction,
    JoinRequestResponse,
    JoinRequestsListResponse,
    MemberResponse,
    MembersListResponse,
    OrgCreateRequest,
    OrgResponse,
    OrgSearchResponse,
    RoleUpdateRequest,
    TokenResponse,
)

router = APIRouter(prefix="/orgs", tags=["orgs"])


async def _require_owner(db: DbSession, org_id: str, user_id: str) -> None:
    """Verify the user is an owner of the org. Raises AuthenticationError if not."""
    membership = await auth_dal.get_membership(db, org_id, user_id)
    if not membership or membership.role != "owner":
        raise AuthenticationError("Owner access required")


@router.post("", response_model=OrgResponse)
async def create_org(body: OrgCreateRequest, auth: JwtAuth, db: DbSession) -> OrgResponse:
    """Create a new organization. The user becomes the owner."""
    existing = await orgs_dal.get_user_membership(db, auth.user_id)
    if existing:
        raise ConflictError("You already belong to an organization")

    org = await auth_dal.create_org(db, body.name)
    await auth_dal.create_membership(db, org.id, auth.user_id, role="owner")
    logger.info("Org created org_id=%s by user_id=%s", org.id, auth.user_id)

    return OrgResponse(id=org.id, name=org.name, plan=org.plan, created_at=org.created_at)


@router.get("/search", response_model=OrgSearchResponse)
async def search_orgs(q: str, auth: JwtAuth, db: DbSession) -> OrgSearchResponse:
    """Search organizations by name (public, any authenticated user)."""
    orgs = await orgs_dal.search_orgs(db, q)
    return OrgSearchResponse(
        orgs=[OrgResponse(id=o.id, name=o.name, plan=o.plan, created_at=o.created_at) for o in orgs]
    )


@router.get("/current", response_model=OrgResponse)
async def get_current_org(auth: JwtAuth, db: DbSession) -> OrgResponse:
    """Get the current user's organization info."""
    if not auth.org_id:
        raise NotFoundError("Organization", "current")

    org = await orgs_dal.get_org_by_id(db, auth.org_id)
    if not org:
        raise NotFoundError("Organization", auth.org_id)

    return OrgResponse(id=org.id, name=org.name, plan=org.plan, created_at=org.created_at)


@router.post("/current/refresh-token", response_model=TokenResponse)
async def refresh_token(auth: JwtAuth, db: DbSession) -> TokenResponse:
    """Issue a new JWT with the user's current org_id."""
    membership = await orgs_dal.get_user_membership(db, auth.user_id)
    org_id = membership.org_id if membership else ""
    token = create_access_token(auth.user_id, org_id, auth.email)
    return TokenResponse(token=token)


@router.get("/current/members", response_model=MembersListResponse)
async def list_members(auth: JwtAuth, db: DbSession) -> MembersListResponse:
    """List members of the current org. Owner only."""
    if not auth.org_id:
        raise AuthenticationError("No organization")
    await _require_owner(db, auth.org_id, auth.user_id)

    members = await orgs_dal.get_org_members(db, auth.org_id)
    return MembersListResponse(
        members=[
            MemberResponse(
                user_id=m.user_id,
                email=m.user.email,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in members
        ]
    )


@router.patch("/current/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    user_id: str, body: RoleUpdateRequest, auth: JwtAuth, db: DbSession
) -> MemberResponse:
    """Update a member's role. Owner only."""
    if not auth.org_id:
        raise AuthenticationError("No organization")
    await _require_owner(db, auth.org_id, auth.user_id)

    member = await orgs_dal.update_member_role(db, auth.org_id, user_id, body.role)
    if not member:
        raise NotFoundError("Member", user_id)

    user = await orgs_dal.get_user_by_id(db, user_id)
    return MemberResponse(
        user_id=member.user_id,
        email=user.email if user else "",
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/current/members/{user_id}", status_code=204)
async def remove_member(user_id: str, auth: JwtAuth, db: DbSession) -> None:
    """Remove a member from the org. Owner only. Cannot remove yourself."""
    if not auth.org_id:
        raise AuthenticationError("No organization")
    await _require_owner(db, auth.org_id, auth.user_id)

    if user_id == auth.user_id:
        raise ConflictError("Cannot remove yourself from the organization")

    removed = await orgs_dal.remove_member(db, auth.org_id, user_id)
    if not removed:
        raise NotFoundError("Member", user_id)


@router.post("/{org_id}/join", response_model=JoinRequestResponse)
async def request_to_join(org_id: str, auth: JwtAuth, db: DbSession) -> JoinRequestResponse:
    """Request to join an organization."""
    existing_membership = await orgs_dal.get_user_membership(db, auth.user_id)
    if existing_membership:
        raise ConflictError("You already belong to an organization")

    org = await orgs_dal.get_org_by_id(db, org_id)
    if not org:
        raise NotFoundError("Organization", org_id)

    existing_request = await orgs_dal.get_pending_request_for_user(db, org_id, auth.user_id)
    if existing_request:
        raise ConflictError("You already have a pending request for this organization")

    request = await orgs_dal.create_join_request(db, org_id, auth.user_id)
    logger.info(
        "Join request created request_id=%s org_id=%s user_id=%s",
        request.id, org_id, auth.user_id,
    )

    return JoinRequestResponse(
        id=request.id,
        user_id=auth.user_id,
        user_email=auth.email,
        status=request.status,
        created_at=request.created_at,
    )


@router.get("/current/join-requests", response_model=JoinRequestsListResponse)
async def list_join_requests(auth: JwtAuth, db: DbSession) -> JoinRequestsListResponse:
    """List pending join requests for the current org. Owner only."""
    if not auth.org_id:
        raise AuthenticationError("No organization")
    await _require_owner(db, auth.org_id, auth.user_id)

    requests = await orgs_dal.get_pending_join_requests(db, auth.org_id)
    return JoinRequestsListResponse(
        requests=[
            JoinRequestResponse(
                id=r.id,
                user_id=r.user_id,
                user_email=r.user.email,
                status=r.status,
                created_at=r.created_at,
            )
            for r in requests
        ]
    )


@router.post("/current/join-requests/{request_id}", response_model=JoinRequestResponse)
async def resolve_join_request(
    request_id: str, body: JoinRequestAction, auth: JwtAuth, db: DbSession
) -> JoinRequestResponse:
    """Accept or decline a join request. Owner only."""
    if not auth.org_id:
        raise AuthenticationError("No organization")
    await _require_owner(db, auth.org_id, auth.user_id)

    join_request = await orgs_dal.get_join_request_by_id(db, request_id)
    if not join_request or join_request.org_id != auth.org_id:
        raise NotFoundError("Join request", request_id)

    if join_request.status != "pending":
        raise ConflictError("Join request has already been resolved")

    new_status = "accepted" if body.action == "accept" else "declined"
    resolved = await orgs_dal.resolve_join_request(db, request_id, new_status, auth.user_id)

    if body.action == "accept":
        await auth_dal.create_membership(db, auth.org_id, join_request.user_id, role="member")
        logger.info(
            "Join request accepted request_id=%s user_id=%s",
            request_id, join_request.user_id,
        )

    return JoinRequestResponse(
        id=resolved.id,
        user_id=resolved.user_id,
        user_email=join_request.user.email,
        status=resolved.status,
        created_at=resolved.created_at,
    )
