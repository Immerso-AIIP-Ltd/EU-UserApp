# app/api/v1/service/forgot_password_service.py

import asyncio
import contextlib
import time

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.device_service import DeviceService
from app.api.v1.service.fusionauth_service import FusionAuthService
from app.api.v1.service.register_otp import GenerateOtpService
from app.core.constants import DeviceNames, ErrorMessages, Intents, Messages
from app.core.exceptions import (
    AccountBlockedError,
    DeviceNotRegisteredError,
    UserNotFoundError,
)
from app.db.models.user_app import User
from app.db.utils import execute_query


class ForgotPasswordService:
    """Service to handle forgot password logic."""

    @staticmethod
    async def forgot_password_email(
        db: AsyncSession,
        email: str,
        cache: Redis,
        device_id: str | None = None,
    ) -> str:
        """Process forgot password request via email."""
        if device_id and not await DeviceService.is_device_registered(device_id, db):
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)

        rows = await execute_query(UserQueries.GET_USER_BY_EMAIL, {"email": email}, db)
        if not rows:
            raise UserNotFoundError

        user = rows[0]
        if user["state"] == "blocked":
            raise AccountBlockedError

        await GenerateOtpService.generate_otp(
            redis_client=cache,
            receiver=email,
            receiver_type="email",
            intent=Intents.FORGOT_PASSWORD,
            db_session=db,
        )

        return Messages.OTP_SENT

    @staticmethod
    async def forgot_password_mobile(
        db: AsyncSession,
        mobile: str,
        calling_code: str,
        ip: str,
        cache: Redis,
        device_id: str | None = None,
    ) -> str:
        """Process forgot password request via mobile."""
        if device_id and not await DeviceService.is_device_registered(device_id, db):
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)

        params = {"mobile": mobile, "calling_code": calling_code}
        rows = await execute_query(UserQueries.GET_USER_BY_MOBILE, params, db)
        if not rows:
            raise UserNotFoundError

        user = rows[0]
        if user["state"] == "blocked":
            raise AccountBlockedError

        await GenerateOtpService.generate_otp(
            redis_client=cache,
            receiver=f"{calling_code}{mobile}",
            receiver_type="mobile",
            intent=Intents.FORGOT_PASSWORD,
            x_forwarded_for=ip,
            db_session=db,
            mobile=mobile,
            calling_code=calling_code,
        )

        return Messages.OTP_SENT

    @staticmethod
    async def set_forgot_password(
        db: AsyncSession,
        email: str,
        password: str,
        client_id: str,
        device_id: str,
        cache: Redis,
    ) -> tuple[str, str, int]:
        """Update user password and return auth token."""
        # 0. Check if device is registered
        if not device_id or not await DeviceService.is_device_registered(
            device_id,
            db,
        ):
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)

        # 1. Get User
        rows = await execute_query(UserQueries.GET_USER_BY_EMAIL, {"email": email}, db)
        if not rows:
            raise UserNotFoundError

        user_data = rows[0]
        user_id = user_data["id"]

        # 2. Update Password
        hashed_password = AuthService.hash_password(password)
        await execute_query(
            UserQueries.UPDATE_USER_PASSWORD,
            {"user_id": user_id, "password": hashed_password},
            db,
        )
        await db.commit()

        # 3. Generate Local Token (Legacy/Audit)
        user = User(id=user_id, email=email)

        token, expires_at = await AuthService.generate_token(
            db_session=db,
            user=user,
            client_id=client_id,
            cache=cache,
            device_id=device_id,
        )

        # 4. FusionAuth Integration
        refresh_token = ""
        with contextlib.suppress(Exception):
            user_uuid_str = str(user_id)

            # Sync User (Ensure exists and is active)
            await asyncio.to_thread(
                FusionAuthService.create_fusion_user,
                user_uuid_str,
                email,
            )

            # Issue RS256 Token
            fa_token = await asyncio.to_thread(
                FusionAuthService.issue_token,
                user_uuid_str,
                user_details={"device_id": device_id},
            )

            if fa_token:
                token = fa_token
                expires_at = int(time.time()) + 600

        # 5. Link device to user

        await DeviceService.link_device_to_user(
            device_id=device_id or "",
            user_uuid=user_id,
            db_session=db,
            cache=cache,
            auth_token=token,
        )

        # 6. Generate Refresh Token
        refresh_token = await AuthService.create_refresh_session(
            db_session=db,
            user_id=str(user_id),
            device_id=device_id or DeviceNames.UNKNOWN_DEVICE,
        )

        return token, refresh_token, expires_at
