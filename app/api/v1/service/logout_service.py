from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.db.utils import execute_query


class UserLogoutService:
    @staticmethod
    async def logout(
        user_uuid: str,
        token: str,
        device_id: str,
        db_session: AsyncSession,
        cache: Redis,
    ) -> None:
        """
        Logs out the user by invalidating the token in Redis and updating the database.
        """
        # 1. Invalidate token in Redis
        cache_key = f"auth:{user_uuid}:{device_id}"
        await cache.delete(cache_key)
        logger.info(f"Invalidated Redis token for user {user_uuid} on device {device_id}")

        # 2. Update token status in Database
        await execute_query(
            UserQueries.DEACTIVATE_USER_TOKEN,
            {"token": token, "device_id": device_id},
            db_session,
        )
        logger.info(f"Deactivated token in DB for device {device_id}")

        # 3. Call stored procedure for additional cleanup if needed
        await execute_query(
            UserQueries.LOGOUT_USER,
            {"user_id": user_uuid, "device_id": device_id},
            db_session,
        )
        logger.info(f"Executed logout stored procedure for user {user_uuid}")

    @staticmethod
    async def deactivate_account(
        user_uuid: str,
        token: str,
        device_id: str,
        db_session: AsyncSession,
        cache: Redis,
    ) -> None:
        """
        Deactivates the user account and logs them out of the current device.
        """
        # 1. Call deactivation stored procedure
        await execute_query(
            UserQueries.DEACTIVATE_USER,
            {"user_id": user_uuid},
            db_session,
        )
        logger.info(f"Executed deactivation stored procedure for user {user_uuid}")

        # 2. Perform logout for current session
        await UserLogoutService.logout(
            user_uuid=user_uuid,
            token=token,
            device_id=device_id,
            db_session=db_session,
            cache=cache,
        )
