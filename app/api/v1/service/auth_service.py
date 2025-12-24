from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
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
    async def generate_token(user_uuid: str, client_id: str, db_session: AsyncSession, cache: Redis, device_id: str):
        """
        Generate JWT + save session in Redis
        """
        expires_at = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())

        payload = {
            "uuid": str(user_uuid),
            "client_id": client_id,
            "device_id": device_id,
            "exp": expires_at,
        }

        # Get client secret from database
        result = await execute_query(UserQueries.GET_CLIENT_SECRET, {"client_id": client_id}, db_session)
        client_secret = result[0]["client_secret"]

        token = jwt.encode(payload, client_secret, algorithm="HS256")

        # Save token in Redis (for logout/session management)
        await cache.set(f"auth:{user_uuid}:{device_id}", token, ex=30 * 24 * 3600)

        return token, expires_at

    @staticmethod
    def decode_token(token: str, client_secret: str):
        """
        Decode JWT token
        """
        try:
            return jwt.decode(token, client_secret, algorithms=["HS256"])
        except Exception as e:
            logger.error(f"JWT decode failed: {e}")
            return None


