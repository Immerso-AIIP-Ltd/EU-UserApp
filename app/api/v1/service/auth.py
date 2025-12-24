import datetime
import pytz
from app.api.v1.register import redis
from app.core.constants import AuthConfig
from app.db.models.user_app import AppConsumer, User, UserAuthToken
import jwt
from app.settings import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class AuthService:

    @staticmethod
    async def generate_token(
        db_session: AsyncSession,
        user: User,
        client_id: str,
        device_id: str = None,
        days_to_expire: int = settings.user_token_days_to_expire,
        partner_attrs: dict = {}
    ):
        # Fetch AppConsumer using SQLAlchemy
        result = await db_session.execute(
            select(AppConsumer).where(AppConsumer.client_id == client_id)
        )
        application = result.scalars().first()
        if not application:
            raise Exception(f"AppConsumer not found for client_id={client_id}")

        partner_code = application.partner_code
        expiry = datetime.datetime.now(pytz.utc) + datetime.timedelta(days=int(days_to_expire))


        token_payload = {
            "uuid": str(user.id),
            "exp": expiry
        }

        encoded_jwt = jwt.encode(
            token_payload,
            application.client_secret,
            algorithm=AuthConfig.ALGORITHM
        )

        # Save token in table (SQLAlchemy style)
        user_token = UserAuthToken(
            device_id=device_id,
            token=encoded_jwt,
            uuid=user.id,
            app_consumer_id=application.id,  # assuming FK field
            expires_at=expiry,
            partner_id=partner_attrs.get('partner_id', 'EROS'),
        )
        db_session.add(user_token)
        await db_session.commit()

        # Save token in Redis
        if partner_code not in settings.skip_partner_auth_redis_check:
            redis.lpush(str(user.id), encoded_jwt)
            timeout_val = int(
                ((expiry + datetime.timedelta(days=settings.token_leeway_threshold_in_days)).timestamp())
                - datetime.datetime.now(pytz.utc).timestamp()
            )
            #redis.set_val(encoded_jwt, str(user.id), timeout=timeout_val)

        return encoded_jwt, int(expiry.timestamp())
