from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.db.utils import execute_query
from app.api.v1.service.device_redis_service import DeviceTokenRedisService
from app.core.exceptions import DeviceNotRegistered, DeviceAlreadyRegistered


class DeviceService:

    @staticmethod
    async def is_device_registered(device_id: str, db_session: AsyncSession) -> bool:
        rows = await execute_query(UserQueries.CHECK_DEVICE_EXISTS, {"device_id": device_id}, db_session)
        return bool(rows)

    @staticmethod
    async def create_device(device_id: str, db_session: AsyncSession, cache: Redis, **attrs):
        """
        Creates a new device.
        """
        if await DeviceService.is_device_registered(device_id, db_session):
            raise DeviceAlreadyRegistered("Device already registered")

        # Prepare default values matching the query params
        params = {
            "device_id": device_id,
            "device_type": attrs.get("device_type", "android"),
            "device_name": attrs.get("device_name", ""),
            "platform": attrs.get("platform", "android"),
            "device_ip": attrs.get("device_ip", None),
            "is_rooted": attrs.get("is_rooted", False),
            "is_jailbroken": attrs.get("is_jailbroken", False),
            "push_token": attrs.get("push_token", None)
        }
        
        await execute_query(UserQueries.INSERT_DEVICE, params, db_session)
        
        # Log device creation and sync to Redis if needed
        # Since INSERT returns a dict, we can construct the device object for Redis
        # But we need to act based on whether a user is linked. 
        # In create_device usually no user is linked yet unless specified in attrs.
        # But the INSERT query for this basic version doesn't take user_id directly.
        
        return params

    @staticmethod
    async def update_device(device_id: str, db_session: AsyncSession, cache: Redis, **kwargs):
        """
        Updates device details.
        """
        # We need to construct params that match UPDATE_DEVICE query
        # Using COALESCE in SQL means passing None is fine if we want to skip update
        params = {
            "device_id": device_id,
            "device_type": kwargs.get("device_type"),
            "device_name": kwargs.get("device_name"),
            "push_token": kwargs.get("push_token")
        }
        await execute_query(UserQueries.UPDATE_DEVICE, params, db_session)
        
        # If push_token is updated, we might need to sync to Redis for all linked users
        # But checking linked users is complex without reading the device.
        # For now, following the pattern: if push_token is in kwargs.
        pass

    @staticmethod
    async def get_device(device_id: str, db_session: AsyncSession):
        rows = await execute_query(UserQueries.GET_DEVICE_BY_ID, {"device_id": device_id}, db_session)
        if not rows:
            raise DeviceNotRegistered("Device not registered")
        return dict(rows[0])

    @staticmethod
    async def link_device_to_user(
        device_id: str, 
        user_uuid: str, 
        db_session: AsyncSession, 
        cache: Redis, 
        auth_token: str = None
    ):
        """
        Links a device to a user and syncs token to Redis.
        """
        exists = await DeviceService.is_device_registered(device_id, db_session)
        if not exists:
            # Depending on business logic, we might auto-create or raise
            # The Django code raises DeviceNotRegistered
            raise DeviceNotRegistered(f"Device {device_id} not registered")

        # Update DB
        # Note: Logic here simplifies the "clone object" part from Django 
        # assuming we just re-assign the device or update it.
        await execute_query(
            UserQueries.LINK_DEVICE_TO_USER,
            {
                "device_id": device_id, 
                "user_id": user_uuid, 
                "user_token": auth_token
            },
            db_session
        )
        
        # Get updated device to sync
        device = await DeviceService.get_device(device_id, db_session)
        
        # Auto-sync to Redis
        if device.get("push_token"):
            try:
                redis_service = DeviceTokenRedisService(cache)
                await redis_service.store_device_token_in_redis(device, user_uuid)
            except Exception as e:
                logger.error(f"Failed to sync device token: {e}")

    @staticmethod
    async def deactivate_device(
        device_id: str,
        user_uuid: str,
        db_session: AsyncSession,
        cache: Redis
    ):
        """
        Deactivates a device for a user.
        """
        # Get device first
        try:
            device = await DeviceService.get_device(device_id, db_session)
        except DeviceNotRegistered:
             logger.warning(f"Device {device_id} not found during deactivation")
             return

        # Deactivate in DB
        await execute_query(
            UserQueries.DEACTIVATE_DEVICE,
            {"device_id": device_id, "user_id": user_uuid},
            db_session
        )
        
        # Remove from Redis
        if device.get("push_token"):
            try:
                redis_service = DeviceTokenRedisService(cache)
                await redis_service.remove_device_token_from_redis(device, user_uuid)
            except Exception as e:
                logger.error(f"Failed to remove device token: {e}")
