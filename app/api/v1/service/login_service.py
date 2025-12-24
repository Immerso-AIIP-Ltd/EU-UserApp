# app/api/v1/service/login_service.py

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service.auth_service import AuthService
from app.core.exceptions.exceptions import UnauthorizedError, UserNotFoundException
from app.db.utils import execute_query


class LoginService:

    @staticmethod
    async def login_user(login_data, client_id, device_id, db_session: AsyncSession, cache: Redis):

        rows = await execute_query(UserQueries.GET_USER_FOR_LOGIN, {
            "email": login_data.email,
            "mobile": login_data.mobile,
            "calling_code": login_data.calling_code,
        }, db_session)

        if not rows:
            raise UserNotFoundException("User not found")

        user = dict(rows[0])
        user_id = user["id"]

        # Password verify
        if not AuthService.verify_password(login_data.password, user["password"]):
            raise UnauthorizedError("Invalid password")

        # Generate token
        token, expires_at = await AuthService.generate_token(
            user_uuid=user_id,
            client_id=client_id,
            db_session=db_session,
            cache=cache,
            device_id=device_id,
        )

        return user, token, expires_at
