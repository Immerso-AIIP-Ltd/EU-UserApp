from fastapi.routing import APIRouter

from app.api.v1 import (
    device,
    docs,
    friend_invite_joinwaitlist,
    internal,
    login,
    logout,
    monitoring,
    register,
    social_login,
    user_profile,
)

api_router = APIRouter()

# Internal & Monitoring (Likely protected by internal network rules or distinct auth)
api_router.include_router(
    monitoring.router,
    prefix="/internal/monitoring",
    tags=["monitoring"],
)
api_router.include_router(internal.router, prefix="/internal/redis", tags=["internal"])

# Public Routes
api_router.include_router(register.router, prefix="/register", tags=["Registration"])
api_router.include_router(login.router, prefix="/user", tags=["Login"])
api_router.include_router(social_login.router, prefix="/social", tags=["Social Login"])
api_router.include_router(device.router, prefix="/device", tags=["Device Invite"])

# Protected Routes (Prefixed with /auth -> /user/v1/auth/...)
api_router.include_router(logout.router, prefix="/auth/user", tags=["Logout"])
api_router.include_router(
    user_profile.router,
    prefix="/auth/user_profile",
    tags=["profile"],
)
api_router.include_router(
    friend_invite_joinwaitlist.router,
    prefix="/auth/social",
    tags=["Friend Invite Join Waitlist"],
)

api_router.include_router(docs.router)
