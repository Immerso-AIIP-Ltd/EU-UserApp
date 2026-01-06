from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.register.otp import GenerateOtpService
from app.core.constants import Intents, Messages
from app.core.exceptions.exceptions import AccountBlockedError, UserNotFoundError
from app.db.utils import execute_query


class ForgotPasswordService:

    @staticmethod
    async def forgot_password_email(db: AsyncSession, email: str, cache: Redis) -> str:
        rows = await execute_query(UserQueries.GET_USER_BY_EMAIL, {"email": email}, db)
        if not rows:
            raise UserNotFoundError()

        user = rows[0]
        if user["state"] == "blocked":
            raise AccountBlockedError()

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
        params = {"mobile": mobile, "calling_code": calling_code}
        rows = await execute_query(UserQueries.GET_USER_BY_MOBILE, params, db)
        if not rows:
            raise UserNotFoundError()

        user = rows[0]
        if user["state"] == "blocked":
            raise AccountBlockedError()

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
