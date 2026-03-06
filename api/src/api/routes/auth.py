"""Google OAuth and JWT authentication endpoints."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Request
from fastapi.responses import RedirectResponse

from api.auth import create_access_token
from api.config import settings
from api.dal import auth as auth_dal
from api.deps import DbSession, JwtAuth  # noqa: TCH001
from api.exceptions import AuthenticationError
from api.logger import logger
from api.schemas.auth import AuthUserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
async def google_login(request: Request) -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    if not settings.google_client_id:
        raise AuthenticationError("Google OAuth is not configured")

    state = secrets.token_urlsafe(32)

    callback_url = str(request.url_for("google_callback"))

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    response = RedirectResponse(url=f"{_GOOGLE_AUTH_URL}?{urlencode(params)}")
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,
    )
    return response


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    db: DbSession,
    oauth_state: str | None = Cookie(default=None),
) -> RedirectResponse:
    """Handle the Google OAuth callback.

    Exchanges the authorization code for tokens, provisions the user/org,
    and redirects to the frontend with a JWT in the URL hash.
    """
    if not oauth_state or state != oauth_state:
        raise AuthenticationError("Invalid OAuth state")

    callback_url = str(request.url_for("google_callback"))

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.warning("Google token exchange failed: %s", token_resp.text)
        raise AuthenticationError("Google authentication failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise AuthenticationError("No access token from Google")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_resp.status_code != 200:
        logger.warning("Google userinfo fetch failed: %s", userinfo_resp.text)
        raise AuthenticationError("Failed to fetch Google user info")

    userinfo = userinfo_resp.json()
    email = userinfo.get("email")
    if not email:
        raise AuthenticationError("No email in Google profile")

    # Find or create user
    user = await auth_dal.get_user_by_email(db, email)
    if not user:
        user = await auth_dal.create_user(db, email)
        logger.info("Created new user email=%s", email)

    # Look up existing membership — user must create or join an org via the UI
    from api.dal import orgs as orgs_dal

    membership = await orgs_dal.get_user_membership(db, user.id)
    org_id = membership.org_id if membership else ""

    jwt_token = create_access_token(user.id, org_id, email)

    response = RedirectResponse(
        url=f"{settings.frontend_url}/#token={jwt_token}",
        status_code=302,
    )
    response.delete_cookie("oauth_state")
    return response


@router.get("/me", response_model=AuthUserResponse)
async def get_current_user(auth: JwtAuth) -> AuthUserResponse:
    """Return the current authenticated user's info (JWT auth only)."""
    return AuthUserResponse(
        user_id=auth.user_id,
        org_id=auth.org_id,
        email=auth.email,
    )
