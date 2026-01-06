import json
from datetime import datetime
from typing import Any

from loguru import logger
from redis.asyncio import Redis


class DeviceTokenRedisService:
    """Service to store device tokens directly in Redis."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client
        self.ttl = 86400  # 24 hours default, can be moved to settings

    async def store_device_token_in_redis(
        self,
        device: dict[str, Any],
        user_uuid: str,
    ) -> dict[str, Any]:
        """
        Store device token directly in Redis.

        Args:
            device: Dictionary containing device data (from DB row)
            user_uuid: UUID of the user
        """
        try:
            device_id = device["device_id"]
            push_token = device.get("push_token")

            if not push_token:
                logger.debug(
                    f"No push token for device {device_id}, skipping Redis store",
                )
                return {"success": False, "message": "No push token"}

            # Store individual device token
            device_key = f"device_token:{user_uuid}:{device_id}"
            device_data = {
                "token": push_token,
                "device_type": device.get("device_type", "android"),
                "device_name": device.get("device_name", ""),
                "platform": device.get("platform", "android"),
                "is_active": device.get("device_active", True),
                "updated_at": datetime.now().isoformat(),
            }

            # Use setex for TTL
            await self.redis_client.setex(device_key, self.ttl, json.dumps(device_data))

            # Update user's device tokens list
            await self._update_user_device_list_in_redis(user_uuid)

            logger.debug(f"Device token stored in Redis for device {device_id}")
            return {"success": True, "message": "Device token stored in Redis"}

        except Exception as e:
            error_message = f"Error storing device token in Redis: {e!s}"
            logger.error(error_message)
            return {"success": False, "error": str(e)}

    async def remove_device_token_from_redis(
        self,
        device: dict[str, Any],
        user_uuid: str,
    ) -> dict[str, Any]:
        """Remove device token from Redis when device is deactivated."""
        try:
            device_id = device["device_id"]

            # Remove individual device token
            device_key = f"device_token:{user_uuid}:{device_id}"
            await self.redis_client.delete(device_key)

            # Update user's device tokens list
            await self._update_user_device_list_in_redis(user_uuid)

            logger.debug(f"Device token removed from Redis for device {device_id}")
            return {"success": True, "message": "Device token removed from Redis"}

        except Exception as e:
            error_message = f"Error removing device token from Redis: {e!s}"
            logger.error(error_message)
            return {"success": False, "error": str(e)}

    async def _update_user_device_list_in_redis(self, user_uuid: str) -> None:
        """Update the user's complete device tokens list in Redis."""
        try:
            # Get all active device tokens for this user from Redis
            device_pattern = f"device_token:{user_uuid}:*"
            # Note: keys() is blocking in standard Redis, but used here
            # as per requirements. Ideally use SCAN for large datasets.
            device_keys = await self.redis_client.keys(device_pattern)

            active_devices = []
            for key in device_keys:
                device_data_str = await self.redis_client.get(key)
                if device_data_str:
                    device_data = json.loads(device_data_str)
                    if device_data.get("is_active", False):
                        active_devices.append(device_data)

            # Store user's device tokens list
            user_devices_key = f"user_device_tokens:{user_uuid}"

            if active_devices:
                await self.redis_client.setex(
                    user_devices_key,
                    self.ttl,
                    json.dumps(active_devices),
                )
                logger.debug(
                    f"Updated user device list in Redis: {len(active_devices)} devices",
                )
            else:
                await self.redis_client.delete(user_devices_key)
                logger.debug("Removed user device list from Redis (no active devices)")

        except Exception as e:
            logger.error(
                "Failed to update user device list in Redis for user {uuid}: {err!s}",
                uuid=user_uuid,
                err=e,
            )

    async def get_user_device_tokens(self, user_uuid: str) -> list[dict[str, Any]]:
        """Get user's device tokens from Redis."""
        try:
            user_devices_key = f"user_device_tokens:{user_uuid}"
            cached_data = await self.redis_client.get(user_devices_key)

            if cached_data:
                return json.loads(cached_data)
            return []

        except Exception as e:
            logger.error(
                f"Failed to get device tokens from Redis for user {user_uuid}: {e!s}",
            )
            return []
