# app/api/v1/service/login_service.py

from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import LoginRequest
from app.api.v1.service.auth_service import AuthService
from app.core.exceptions.exceptions import UnauthorizedError, UserNotFoundError
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
    ) -> tuple[dict[str, Any], str, int]:
        """Authenticates a user and generates a login token."""

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
            raise UserNotFoundError("User not found")

        user = dict(rows[0])
        user_id = user["id"]

        # Password verify
        if not login_data.password or not AuthService.verify_password(
            login_data.password,
            user["password"],
        ):
            raise UnauthorizedError("Invalid password")

        # Generate token
        from app.db.models.user_app import User

        token, expires_at = await AuthService.generate_token(
            user=User(id=user_id),
            client_id=client_id or "",
            db_session=db_session,
            cache=cache,
            device_id=device_id or "",
        )

        # FusionAuth Integration
        try:
            from app.api.v1.service.fusionauth_service import FusionAuthService
            import asyncio
            import time
            
            user_uuid_str = str(user_id)
            user_email = user.get("email")
            
            # 1. Sync User (Ensure exists)
            await asyncio.to_thread(FusionAuthService.create_fusion_user, user_uuid_str, user_email)
            
            # 2. Issue Token
            fa_token = await asyncio.to_thread(FusionAuthService.issue_token, user_uuid_str)
            
            if not fa_token:
                 raise UnauthorizedError("Failed to issue FusionAuth token: No token received")
            
            token = fa_token
            # FA default TTL is 300s -> updated to 600s
            expires_at = int(time.time()) + 600

        except Exception as e:
             # Raise an error if FusionAuth token cannot be issued
             # print(f"Failed to issue FusionAuth token: {e}")
             raise UnauthorizedError(f"Failed to issue FusionAuth token: {e}")

        # Link device to user
        from app.api.v1.service.device_service import DeviceService

        await DeviceService.link_device_to_user(
            device_id=device_id or "",
            user_uuid=user_id,
            db_session=db_session,
            cache=cache,
            auth_token=token,
        )

        return user, token, expires_at
