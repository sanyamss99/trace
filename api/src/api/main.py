from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from api.config import settings
from api.database import engine
from api.exceptions import TraceAppError
from api.logger import logger
from api.request_id import RequestIdMiddleware
from api.routes import api_router

# 10 MB — covers 1000 spans at ~10 KB average with generous headroom.
MAX_BODY_BYTES = 10_485_760


class MaxBodySizeMiddleware:
    """ASGI middleware that rejects request bodies exceeding a byte limit."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length_raw = headers.get(b"content-length")
        if content_length_raw is not None:
            try:
                content_length = int(content_length_raw)
            except ValueError:
                content_length = 0
            if content_length > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"error": f"Request body too large (max {self.max_bytes} bytes)"},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle — disposes the DB engine on exit."""
    yield
    await engine.dispose()
    logger.info("Database engine disposed")


def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title="Trace",
        description="Real-time causal debugger for LLM applications",
        version="0.1.0",
        lifespan=_lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["X-Trace-Key", "Content-Type", "Accept"],
    )

    application.include_router(api_router)

    @application.exception_handler(TraceAppError)
    async def trace_error_handler(_request: Request, exc: TraceAppError) -> JSONResponse:
        logger.warning("Application error: %s", exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Validation error: %s", exc.errors())
        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": exc.errors()},
        )

    @application.exception_handler(Exception)
    async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s", type(exc).__name__, exc_info=settings.is_debug)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )

    # Body size middleware wraps the entire app (outermost layer).
    application.add_middleware(MaxBodySizeMiddleware)

    # Request ID middleware — outermost, so every log line has a correlation ID.
    application.add_middleware(RequestIdMiddleware)

    return application


app = create_app()
