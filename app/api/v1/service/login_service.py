# app/api/v1/service/login_service.py


import asyncio
import time
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import LoginRequest
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.device_service import DeviceService
from app.api.v1.service.fusionauth_service import FusionAuthService
from app.core.constants import DeviceNames, ErrorMessages
from app.core.exceptions.exceptions import (
    DeviceNotRegisteredError,
    UnauthorizedError,
    UserNotFoundError,
)
from app.db.models.user_app import User
from app.db.utils import execute_query


class LoginService:
    """Service for handling user login."""

    @staticmethod
    async def _resolve_device_id(
        device_id: str,
        db_session: AsyncSession,
    ) -> str:
        """Resolve device_id string to its UUID string."""
        try:
            # Try to fetch by Serial Number/UUID if it's already a valid UUID
            device_obj = await DeviceService.get_device(device_id, db_session)
            return str(device_obj["id"])
        except Exception:
            # Check if it is the HWID string
            if not await DeviceService.is_device_registered(device_id, db_session):
                raise DeviceNotRegisteredError(
                    ErrorMessages.DEVICE_NOT_REGISTERED,
                ) from None
            return device_id

    @staticmethod
    async def login_user(
        login_data: LoginRequest,
        client_id: str | None,
        device_id: str | None,
        db_session: AsyncSession,
        cache: Redis,
    ) -> tuple[dict[str, Any], str, str, int]:
        """Authenticates a user and generates a login token."""

        # 0. Check if device is registered
        if not device_id:
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_ID_MISSING)

        real_device_uuid = await LoginService._resolve_device_id(device_id, db_session)

        rows = await execute_query(
            UserQueries.GET_USER_FOR_LOGIN,
            {
                "email": login_data.email,
                "mobile": login_data.mobile,
                "calling_code": login_data.calling_code,
            },
            db_session,
        )

        if not rows:
            raise UserNotFoundError(ErrorMessages.USER_NOT_FOUND)

        user = dict(rows[0])
        user_id = user["id"]

        # Password verify
        if not login_data.password or not AuthService.verify_password(
            login_data.password,
            user["password"],
        ):
            raise UnauthorizedError(ErrorMessages.INCORRECT_PASSWORD)

        # Generate token
        token, expires_at = await AuthService.generate_token(
            user=User(id=user_id),
            client_id=client_id or "",
            db_session=db_session,
            cache=cache,
            device_id=real_device_uuid or "",
        )

        # FusionAuth Integration
        try:
            user_uuid_str = str(user_id)
            user_email = user.get("email")

            # 1. Sync User (Ensure exists) - Cache sync status to avoid redundant calls
            sync_cache_key = f"fa_synced:{user_uuid_str}"
            is_synced = await cache.get(sync_cache_key)

            if not is_synced:
                await asyncio.to_thread(
                    FusionAuthService.create_fusion_user,
                    user_uuid_str,
                    user_email,
                )
                # Cache for 24 hours
                await cache.set(sync_cache_key, "true", ex=86400)

            # 2. Issue Token & Create Refresh Session in Parallel
            # Both call FusionAuth, so parallelizing them saves network latency
            async def generate_refresh() -> str:
                return await AuthService.create_refresh_session(
                    db_session=db_session,
                    user_id=str(user_id),
                    device_id=device_id or DeviceNames.UNKNOWN_DEVICE,
                    device_claim_id=real_device_uuid,
                )

            async def issue_fa_token() -> str:
                return await asyncio.to_thread(
                    FusionAuthService.issue_token,
                    user_uuid_str,
                    user_details={"device_id": real_device_uuid},
                )

            fa_token_task = asyncio.create_task(issue_fa_token())
            refresh_token_task = asyncio.create_task(generate_refresh())

            fa_token, refresh_token = await asyncio.gather(
                fa_token_task,
                refresh_token_task,
            )

            if not fa_token:
                raise UnauthorizedError(
                    f"{ErrorMessages.FUSION_AUTH_TOKEN_ERROR}: No token received",
                )

            token = fa_token
            # FA default TTL is 300s -> updated to 600s
            expires_at = int(time.time()) + 600

        except Exception as e:
            # Raise an error if FusionAuth token cannot be issued
            raise UnauthorizedError(
                f"{ErrorMessages.FUSION_AUTH_TOKEN_ERROR}: {e}",
            ) from e

        # 3. Link device to user (Parallelizable with final steps but safer here)
        await DeviceService.link_device_to_user(
            device_id=device_id or "",
            user_uuid=user_id,
            db_session=db_session,
            cache=cache,
            auth_token=token,
        )

        return user, token, refresh_token, expires_at
