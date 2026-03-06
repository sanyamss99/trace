from fastapi import APIRouter

from api.routes.api_keys import router as api_keys_router
from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router
from api.routes.orgs import router as orgs_router
from api.routes.traces import router as traces_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingest_router, tags=["ingest"])
api_router.include_router(traces_router)
api_router.include_router(api_keys_router)
api_router.include_router(auth_router)
api_router.include_router(orgs_router)
