import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from app.api.queries import UserQueries
from app.db.utils import execute_query


class AuthService:

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
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

    @staticmethod
    async def verify_user_token(headers: dict, db_session: AsyncSession) -> str:
        """
        Verify user token from headers and return user_id.
        """
        api_client = headers.get("x-api-client") or headers.get("api_client")
        api_token = headers.get("x-api-token") or headers.get("api_token")
        
        if not api_client or not api_token:
             from app.core.exceptions import UnauthorizedError
             raise UnauthorizedError()

        # Get client secret
        result = await execute_query(UserQueries.GET_CLIENT_SECRET, {"client_id": api_client}, db_session)
        if not result:
             from app.core.exceptions import UnauthorizedError
             raise UnauthorizedError()
        
        client_secret = result[0]["client_secret"]
        
        payload = AuthService.decode_token(api_token, client_secret)
        if not payload:
             from app.core.exceptions import UnauthorizedError
             raise UnauthorizedError()
             
        return payload.get("uuid")

    @staticmethod
    async def free_token(user_uuid: str, token: str, db_session: AsyncSession, cache: Redis, device_id: str = None):
        """
        Deactivate token in DB and remove from Redis.
        """
        # 1. Update DB (Deactivate specific token)
        # Note: We need a query that matches uuid + token. 
        # UserQueries.DEACTIVATE_USER_AUTH_TOKEN covers this.
        await execute_query(
            UserQueries.DEACTIVATE_USER_AUTH_TOKEN,
            {"user_id": user_uuid, "token": token},
            db_session
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


