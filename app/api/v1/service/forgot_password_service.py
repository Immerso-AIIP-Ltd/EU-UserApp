# app/api/v1/service/forgot_password_service.py

import asyncio
import time
from typing import Any

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
    AccountDeactivatedError,
    DeviceNotRegisteredError,
    UserNotFoundError,
)
from app.db.models.user_app import User
from app.db.utils import execute_query
from app.settings import settings


class ForgotPasswordService:
    """Service to handle forgot password logic."""

    @staticmethod
    def _validate_user_state(user: dict[str, Any] | Any) -> None:
        """Check if user account is blocked or deactivated."""
        if user["state"] == "blocked":
            raise AccountBlockedError
        if user["state"] == "deactivated":
            raise AccountDeactivatedError

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
        ForgotPasswordService._validate_user_state(user)

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
        ForgotPasswordService._validate_user_state(user)

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
    async def _get_user_for_reset(
        db: AsyncSession,
        email: str | None,
        mobile: str | None,
        calling_code: str | None,
    ) -> Any:
        """Find user account by email or mobile."""
        user_data = None
        if email:
            rows = await execute_query(
                UserQueries.GET_USER_BY_EMAIL,
                {"email": email},
                db,
            )
            if rows:
                user_data = rows[0]
        elif mobile and calling_code:
            rows = await execute_query(
                UserQueries.GET_USER_BY_MOBILE,
                {"mobile": mobile, "calling_code": calling_code},
                db,
            )
            if rows:
                user_data = rows[0]

        if not user_data:
            raise UserNotFoundError

        ForgotPasswordService._validate_user_state(user_data)
        return user_data

    @staticmethod
    async def _integrate_fusion_auth(
        user_id: Any,
        email: str | None,
        device_id: str,
        db: AsyncSession,
        cache: Redis,
    ) -> tuple[str | None, str | None]:
        """Sync user with FusionAuth and generate tokens."""
        try:
            user_uuid_str = str(user_id)
            sync_cache_key = f"fa_synced:{user_uuid_str}"
            is_synced = await cache.get(sync_cache_key)

            if not is_synced:
                await asyncio.to_thread(
                    FusionAuthService.create_fusion_user,
                    user_uuid_str,
                    email,
                )
                await cache.set(sync_cache_key, "true", ex=86400)

            # Parallelize token and session generation
            fa_token_task = asyncio.create_task(
                asyncio.to_thread(
                    FusionAuthService.issue_token,
                    user_uuid_str,
                    user_details={"device_id": device_id},
                ),
            )
            refresh_task = asyncio.create_task(
                AuthService.create_refresh_session(
                    db_session=db,
                    user_id=user_uuid_str,
                    device_id=device_id or DeviceNames.UNKNOWN_DEVICE,
                ),
            )

            return await asyncio.gather(fa_token_task, refresh_task)

        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"FusionAuth error: {e}")
            return None, None

    @staticmethod
    async def set_forgot_password(
        db: AsyncSession,
        email: str | None,
        mobile: str | None,
        calling_code: str | None,
        password: str,
        client_id: str,
        device_id: str,
        cache: Redis,
    ) -> tuple[str, str, int, Any]:
        """Update user password and return auth token."""
        if not device_id or not await DeviceService.is_device_registered(
            device_id,
            db,
        ):
            raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)

        user_data = await ForgotPasswordService._get_user_for_reset(
            db,
            email,
            mobile,
            calling_code,
        )
        user_id = user_data["id"]
        final_email = user_data.get("email") or email

        hashed_password = AuthService.hash_password(password)
        await execute_query(
            UserQueries.UPDATE_USER_PASSWORD,
            {"user_id": user_id, "password": hashed_password},
            db,
        )
        await db.commit()

        user = User(id=user_id, email=final_email)
        token, expires_at = await AuthService.generate_token(
            db_session=db,
            user=user,
            client_id=client_id,
            cache=cache,
            device_id=device_id,
        )

        fa_token, refresh_token = await ForgotPasswordService._integrate_fusion_auth(
            user_id,
            final_email,
            device_id,
            db,
            cache,
        )

        if fa_token:
            token = fa_token
            expires_at = int(time.time()) + (
                settings.jwt_access_token_expire_minutes * 60
            )

        await DeviceService.link_device_to_user(
            device_id=device_id or "",
            user_uuid=user_id,
            db_session=db,
            cache=cache,
            auth_token=token,
        )

        return token, refresh_token or "", expires_at, user_id
