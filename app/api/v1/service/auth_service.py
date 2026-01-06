from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
import jwt
import pytz
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.core.constants import (
    AuthConfig,
    AuthLogMessages,
    CacheKeyTemplates,
    CacheValues,
    HeaderKeys,
    LoginParams,
    RequestParams,
)
from app.core.exceptions.exceptions import InvalidServiceTokenError
from app.db.models.user_app import AppConsumer, User, UserAuthToken
from app.db.utils import execute_query
from app.settings import settings


class AuthService:
    """Service to handle user authentication, token generation, and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(
            password.encode(LoginParams.UTF8),
            bcrypt.gensalt(),
        ).decode(LoginParams.UTF8)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plain password against a bcrypt hash."""
        try:
            return bcrypt.checkpw(
                plain.encode(LoginParams.UTF8),
                hashed.encode(LoginParams.UTF8),
            )
        except Exception as e:
            logger.error(AuthLogMessages.BCRYPT_VERIFICATION_FAILED.format(e))
            return False

    @staticmethod
    async def generate_token(
        db_session: AsyncSession,
        user: User,
        client_id: str,
        cache: Redis,
        device_id: str | None = None,
        days_to_expire: int = settings.user_token_days_to_expire,
        partner_attrs: Dict[str, Any] | None = None,
    ) -> tuple[str, int]:
        """Generate a new JWT auth token for a user."""
        if partner_attrs is None:
            partner_attrs = {}
        # Fetch AppConsumer using SQLAlchemy
        result = await db_session.execute(
            select(AppConsumer).where(AppConsumer.client_id == client_id),
        )
        application = result.scalars().first()
        if not application:
            raise Exception(f"AppConsumer not found for client_id={client_id}")

        expiry = datetime.now(pytz.utc) + timedelta(days=int(days_to_expire))

        token_payload = {RequestParams.UUID: str(user.id), RequestParams.EXP: expiry}

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
            partner_id=partner_attrs.get(RequestParams.PARTNER_ID, CacheValues.EROS),
        )
        db_session.add(user_token)
        await db_session.commit()

        return encoded_jwt, int(expiry.timestamp())

    @staticmethod
    def decode_token(token: str, client_secret: str) -> Optional[Dict[str, Any]]:
        """Decode a JWT token."""
        try:
            return jwt.decode(token, client_secret, algorithms=[AuthConfig.ALGORITHM])
        except Exception as e:
            logger.error(AuthLogMessages.JWT_DECODE_FAILED.format(e))
            return None

    @staticmethod
    async def verify_user_token(
        headers: Dict[str, Any],
        db_session: AsyncSession,
        device_id: Optional[str] = None,
    ) -> str:
        """Verify user token from headers and return user_id."""
        api_client = headers.get(HeaderKeys.X_API_CLIENT) or headers.get(
            HeaderKeys.API_CLIENT,
        )
        api_token = headers.get(HeaderKeys.X_API_TOKEN) or headers.get(
            HeaderKeys.API_TOKEN,
        )

        if not api_client or not api_token:
            from app.core.exceptions import UnauthorizedError

            raise UnauthorizedError

        # Get client secret
        result = await execute_query(
            UserQueries.GET_CLIENT_SECRET,
            {RequestParams.CLIENT_ID: api_client},
            db_session,
        )
        if not result:
            from app.core.exceptions import UnauthorizedError

            raise UnauthorizedError

        client_secret = result[0][RequestParams.CLIENT_SECRET]

        payload = AuthService.decode_token(api_token, client_secret)
        if not payload:
            from app.core.exceptions import UnauthorizedError

            raise UnauthorizedError

        uuid = payload.get(RequestParams.UUID)
        if not isinstance(uuid, str):
            raise InvalidServiceTokenError
        return uuid

    @staticmethod
    async def free_token(
        user_uuid: str,
        token: str,
        db_session: AsyncSession,
        cache: Redis,
        device_id: Optional[str] = None,
    ) -> None:
        """Deactivate token in DB and remove from Redis."""
        # 1. Update DB (Deactivate specific token)
        # Note: We need a query that matches uuid + token.
        # UserQueries.DEACTIVATE_USER_AUTH_TOKEN covers this.
        await execute_query(
            UserQueries.DEACTIVATE_USER_AUTH_TOKEN,
            {RequestParams.USER_ID: user_uuid, RequestParams.TOKEN: token},
            db_session,
        )

        # 2. Remove from Redis
        # If device_id is known, we can remove the specific key.
        # If not, we might need to rely on the token structure or loop?
        # The Django code does: redis.lrem(token_obj.uuid, 1, auth_token)
        # and redis.remove_key(auth_token)
        # Our redis pattern is `auth:{user_uuid}:{device_id}` -> token
        # If we only have token, we can't easily find the key without
        # scanning or storing reverse mapping.
        # However, `logout` usually provides device_id.
        if device_id:
            await cache.delete(
                CacheKeyTemplates.USER_AUTH_TOKEN.format(
                    user_uuid=user_uuid,
                    device_id=device_id,
                ),
            )
        else:
            # Fallback: Scan or ignore?
            # For now, we assume device_id is provided or we accept
            # that redis key expires naturally.
            pass
