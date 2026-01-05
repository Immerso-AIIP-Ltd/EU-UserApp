from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import pytz
import jwt
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from redis.asyncio import Redis
from app.cache.utils import lpush
from app.core.constants import AuthConfig
from app.db.models.user_app import AppConsumer, User, UserAuthToken
from app.settings import settings
from sqlalchemy import select
from app.api.queries import UserQueries
from app.core.exceptions.exceptions import InvalidServiceToken
from app.db.utils import execute_query


class AuthService:

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception as e:
            logger.error(f"Bcrypt verification failed: {e}")
            return False

    @staticmethod
    async def generate_token(
        db_session: AsyncSession,
        user: User,
        client_id: str,
        cache: Redis,
        device_id: str | None = None,
        days_to_expire: int = settings.user_token_days_to_expire,
        partner_attrs: Dict[str, Any] = {},
    ) -> tuple[str, int]:
        # Fetch AppConsumer using SQLAlchemy
        result = await db_session.execute(
            select(AppConsumer).where(AppConsumer.client_id == client_id)
        )
        application = result.scalars().first()
        if not application:
            raise Exception(f"AppConsumer not found for client_id={client_id}")

        partner_code = application.partner_code
        expiry = datetime.now(pytz.utc) + timedelta(days=int(days_to_expire))

        token_payload = {"uuid": str(user.id), "exp": expiry}

        encoded_jwt = jwt.encode(
            token_payload,
            str(application.client_secret),
            algorithm=AuthConfig.ALGORITHM,
        )

        # Save token in table (SQLAlchemy style)
        user_token = UserAuthToken(
            device_id=device_id,
            token=encoded_jwt,
            uuid=user.id,
            app_consumer_id=application.id,  # assuming FK field
            expires_at=expiry,
            partner_id=partner_attrs.get("partner_id", "EROS"),
        )
        db_session.add(user_token)
        await db_session.commit()

        # Save token in Redis
        # if partner_code not in settings.skip_partner_auth_redis_check:
        #     # use helper lpush from redis.py
        #     await lpush(cache, str(user.id), encoded_jwt)
        #     timeout_val = int(
        #         (
        #             (
        #                 expiry
        #                 + timedelta(
        #                     days=settings.token_leeway_threshold_in_days
        #                 )
        #             ).timestamp()
        #         )
        #         - datetime.now(pytz.utc).timestamp()
        #     )
        #     # redis.set_val(encoded_jwt, str(user.id), timeout=timeout_val)

        return encoded_jwt, int(expiry.timestamp())

    @staticmethod
    def decode_token(token: str, client_secret: str) -> Optional[Dict[str, Any]]:
        """
        Decode JWT token
        """
        try:
            return jwt.decode(token, client_secret, algorithms=["HS256"])
        except Exception as e:
            logger.error(f"JWT decode failed: {e}")
            return None

    @staticmethod
    async def verify_user_token(
        headers: Dict[str, Any],
        db_session: AsyncSession,
        device_id: Optional[str] = None,
    ) -> str:
        """
        Verify user token from headers and return user_id.
        """
        api_client = headers.get("x-api-client") or headers.get("api_client")
        api_token = headers.get("x-api-token") or headers.get("api_token")

        if not api_client or not api_token:
            from app.core.exceptions import UnauthorizedError

            raise UnauthorizedError()

        # Get client secret
        result = await execute_query(
            UserQueries.GET_CLIENT_SECRET,
            {"client_id": api_client},
            db_session,
        )
        if not result:
            from app.core.exceptions import UnauthorizedError

            raise UnauthorizedError()

        client_secret = result[0]["client_secret"]

        payload = AuthService.decode_token(api_token, client_secret)
        if not payload:
            from app.core.exceptions import UnauthorizedError

            raise UnauthorizedError()

        uuid = payload.get("uuid")
        if not isinstance(uuid, str):
            raise InvalidServiceToken()
        return uuid

    @staticmethod
    async def free_token(
        user_uuid: str,
        token: str,
        db_session: AsyncSession,
        cache: Redis,
        device_id: Optional[str] = None,
    ) -> None:
        """
        Deactivate token in DB and remove from Redis.
        """
        # 1. Update DB (Deactivate specific token)
        # Note: We need a query that matches uuid + token.
        # UserQueries.DEACTIVATE_USER_AUTH_TOKEN covers this.
        await execute_query(
            UserQueries.DEACTIVATE_USER_AUTH_TOKEN,
            {"user_id": user_uuid, "token": token},
            db_session,
        )

        # 2. Remove from Redis
        # If device_id is known, we can remove the specific key.
        # If not, we might need to rely on the token structure or loop?
        # The Django code does: redis.lrem(token_obj.uuid, 1, auth_token) and redis.remove_key(auth_token)
        # Our redis pattern is `auth:{user_uuid}:{device_id}` -> token
        # If we only have token, we can't easily find the key without scanning or storing reverse mapping.
        # However, `logout` usually provides device_id.
        if device_id:
            await cache.delete(f"auth:{user_uuid}:{device_id}")
        else:
            # Fallback: Scan or ignore?
            # For now, we assume device_id is provided or we accept that redis key expires naturally.
            pass
