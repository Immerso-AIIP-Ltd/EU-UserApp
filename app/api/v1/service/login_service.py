# app/api/v1/service/login_service.py

import asyncio
import datetime
import time
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import LoginRequest
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.device_service import DeviceService
from app.api.v1.service.fusionauth_service import FusionAuthService
from app.core.constants import AuthConfig, DeviceNames, ErrorMessages
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

        if not await DeviceService.is_device_registered(device_id, db_session):
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)

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

        if user.get("account_locked_until") and user[
            "account_locked_until"
        ] > datetime.datetime.now(datetime.timezone.utc):
            raise UnauthorizedError(ErrorMessages.ACCOUNT_LOCKED)

        # Password verify
        if not login_data.password or not AuthService.verify_password(
            login_data.password,
            user["password"],
        ):
            await execute_query(
                UserQueries.RECORD_LOGIN_FAILURE,
                {
                    "user_id": user_id,
                    "max_attempts": AuthConfig.MAX_LOGIN_ATTEMPTS,
                },
                db_session,
            )
            raise UnauthorizedError(ErrorMessages.INCORRECT_PASSWORD)

        # Record login success
        await execute_query(
            UserQueries.RECORD_LOGIN_SUCCESS,
            {"user_id": user_id},
            db_session,
        )

        # Generate token
        token, expires_at = await AuthService.generate_token(
            user=User(id=user_id),
            client_id=client_id or "",
            db_session=db_session,
            cache=cache,
            device_id=device_id or "",
        )

        # FusionAuth Integration
        try:
            user_uuid_str = str(user_id)
            user_email = user.get("email")

            # 1. Sync User (Ensure exists)
            await asyncio.to_thread(
                FusionAuthService.create_fusion_user,
                user_uuid_str,
                user_email,
            )

            # 2. Issue Token
            fa_token = await asyncio.to_thread(
                FusionAuthService.issue_token,
                user_uuid_str,
                user_details={"device_id": device_id},
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

        # Link device to user
        await DeviceService.link_device_to_user(
            device_id=device_id or "",
            user_uuid=user_id,
            db_session=db_session,
            cache=cache,
            auth_token=token,
        )

        # Generate Refresh Token
        refresh_token = await AuthService.create_refresh_session(
            db_session=db_session,
            user_id=str(user_id),
            device_id=device_id or DeviceNames.UNKNOWN_DEVICE,
        )

        return user, token, refresh_token, expires_at
