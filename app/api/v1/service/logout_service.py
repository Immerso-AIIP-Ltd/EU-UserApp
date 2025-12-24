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
        And deactivates the device.
        """
        from app.api.v1.service.device_service import DeviceService
        from app.api.v1.service.auth_service import AuthService

        # 1. Deactivate device (covers redis token removal for device flow)
        if device_id:
            await DeviceService.deactivate_device(
                device_id=device_id,
                user_uuid=user_uuid,
                db_session=db_session,
                cache=cache
            )

        # 2. Free auth token (DB + Redis)
        await AuthService.free_token(
            user_uuid=user_uuid,
            token=token,
            db_session=db_session,
            cache=cache,
            device_id=device_id
        )
        
        # 3. Update authentication session (replace stored procedure)
        await execute_query(
            UserQueries.UPDATE_AUTH_SESSION_LOGOUT,
            {"user_id": user_uuid, "device_id": device_id},
            db_session,
        )
        logger.info(f"Executed logout for user {user_uuid} on device {device_id}")

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
        # 1. Mark user as deactivated in DB
        await execute_query(
            UserQueries.UPDATE_USER_DEACTIVATED,
            {"user_id": user_uuid},
            db_session,
        )
        logger.info(f"Deactivated user account {user_uuid}")

        # 2. Perform logout for current session
        await UserLogoutService.logout(
            user_uuid=user_uuid,
            token=token,
            device_id=device_id,
            db_session=db_session,
            cache=cache,
        )
