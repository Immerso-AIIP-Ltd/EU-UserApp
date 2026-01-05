# app/api/v1/service/login_service.py

from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import LoginRequest
from app.api.v1.service.auth_service import AuthService
from app.core.exceptions.exceptions import UnauthorizedError, UserNotFoundException
from app.db.utils import execute_query


class LoginService:

    @staticmethod
    async def login_user(
        login_data: LoginRequest,
        client_id: str | None,
        device_id: str | None,
        db_session: AsyncSession,
        cache: Redis,
    ) -> tuple[dict[str, Any], str, int]:

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
            raise UserNotFoundException("User not found")

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
