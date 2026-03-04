"""Per-request ID via contextvars for correlation across logs."""

from contextvars import ContextVar
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current request ID (empty string outside a request)."""
    return request_id_ctx.get()


class RequestIdMiddleware:
    """ASGI middleware that assigns a UUID to each request.

    - Reuses an incoming ``X-Request-ID`` header if present.
    - Stores the ID in a contextvar so the logger can include it.
    - Adds ``X-Request-ID`` to the response headers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check for incoming X-Request-ID header
        headers = dict(scope.get("headers", []))
        incoming = headers.get(b"x-request-id")
        rid = incoming.decode() if incoming else str(uuid4())

        token = request_id_ctx.set(rid)

        async def send_with_request_id(message: dict) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", rid.encode()))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_ctx.reset(token)
