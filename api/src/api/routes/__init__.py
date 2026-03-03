from fastapi import APIRouter

from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router
from api.routes.traces import router as traces_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingest_router, tags=["ingest"])
api_router.include_router(traces_router)
