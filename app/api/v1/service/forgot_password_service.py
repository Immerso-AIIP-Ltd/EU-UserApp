from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.register.otp import GenerateOtpService
from app.core.constants import Intents, Messages
from app.core.exceptions import AccountBlockedError, UserNotFoundError
from app.db.utils import execute_query


class ForgotPasswordService:
    """Service to handle forgot password logic."""

    @staticmethod
    async def forgot_password_email(db: AsyncSession, email: str, cache: Redis) -> str:
        """Process forgot password request via email."""
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
    ) -> str:
        """Process forgot password request via mobile."""
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
    ) -> tuple[str, int]:
        """Update user password and return auth token."""
        from app.api.v1.service.auth_service import AuthService
        from app.db.models.user_app import User

        # 1. Get User
        rows = await execute_query(UserQueries.GET_USER_BY_EMAIL, {"email": email}, db)
        if not rows:
            raise UserNotFoundError

        user_id = rows[0]["id"]

        # 2. Update Password
        hashed_password = AuthService.hash_password(password)
        await execute_query(
            UserQueries.UPDATE_USER_PASSWORD,
            {"user_id": user_id, "password": hashed_password},
            db,
        )
        await db.commit()

        # 3. Generate Token
        user = User(id=user_id, email=email)
        token, expires_at = await AuthService.generate_token(
            db_session=db,
            user=user,
            client_id=client_id,
            cache=cache,
            device_id=device_id,
        )

        return token, expires_at
