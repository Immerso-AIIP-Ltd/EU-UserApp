from fastapi.routing import APIRouter

from app.api.v1 import (
    docs,
    internal,
    monitoring,
)

api_router = APIRouter()
api_router.include_router(
    monitoring.router,
    prefix="/internal/monitoring",
    tags=["monitoring"],
)
api_router.include_router(internal.router, prefix="/internal/redis", tags=["internal"])
api_router.include_router(docs.router)
