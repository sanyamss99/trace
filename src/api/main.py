from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.exceptions import TraceAppError
from src.api.logger import logger
from src.api.routes import api_router


def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title="Trace",
        description="Real-time causal debugger for LLM applications",
        version="0.1.0",
    )

    application.include_router(api_router)

    @application.exception_handler(TraceAppError)
    async def trace_error_handler(_request: Request, exc: TraceAppError) -> JSONResponse:
        logger.warning("Application error: %s", exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )

    return application


app = create_app()
