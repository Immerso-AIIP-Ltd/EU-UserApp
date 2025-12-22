from fastapi.routing import APIRouter
from app.api.v1.user_profile.views import router as user_profile_router

from app.api.v1 import (
    device,
    docs,
    internal,
    monitoring,
    user,
    user_profile
)

api_router = APIRouter()
api_router.include_router(
    monitoring.router,
    prefix="/internal/monitoring",
    tags=["monitoring"],
)
api_router.include_router(internal.router, prefix="/internal/redis", tags=["internal"])
api_router.include_router(device.router, prefix="/device", tags=["Device Invite"])
api_router.include_router(user.router, prefix="/user", tags=["Registration"])
api_router.include_router(user_profile.router,prefix="/user_profile",tags=["profile"])
api_router.include_router(docs.router)
