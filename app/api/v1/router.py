from fastapi.routing import APIRouter

from app.api.v1 import (
    device,
    docs,
    internal,
    monitoring,
    register,
)

api_router = APIRouter()
api_router.include_router(
    monitoring.router,
    prefix="/internal/monitoring",
    tags=["monitoring"],
)
api_router.include_router(internal.router, prefix="/internal/redis", tags=["internal"])
api_router.include_router(device.router, prefix="/device", tags=["Device Invite"])
api_router.include_router(register.router, prefix="/register", tags=["Registration"])
api_router.include_router(docs.router)
