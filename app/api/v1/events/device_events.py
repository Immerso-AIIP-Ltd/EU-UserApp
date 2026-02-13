"""
Device Token Redis Sync Events (FastAPI/SQLAlchemy)

Similar to Django signals, this module auto-syncs device tokens to Redis
when devices are created, updated, or deleted using SQLAlchemy events.

This ensures Redis is always in sync with the database without manual calls.
"""

import asyncio
from typing import Any

from loguru import logger
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.api.v1.service.device_redis_service import DeviceTokenRedisService
from app.db.models.user_app import Device


def sync_device_token_to_redis(device_dict: dict[str, Any], user_uuid: str) -> None:
    """
    Sync device token to Redis (sync wrapper for async function).
    
    Args:
        device_dict: Device data as dictionary
        user_uuid: User UUID string
    """
    try:
        # Get Redis client from the session or create new connection
        from app.cache.dependencies import get_sync_redis_client
        
        redis_client = get_sync_redis_client()
        if not redis_client:
            logger.warning("Redis client not available, skipping sync")
            return
            
        redis_service = DeviceTokenRedisService(redis_client)
        
        # Determine action based on device state
        if device_dict.get("device_active"):
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    redis_service.store_device_token_in_redis(device_dict, user_uuid)
                )
                action = "stored"
            finally:
                loop.close()
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    redis_service.remove_device_token_from_redis(device_dict, user_uuid)
                )
                action = "removed"
            finally:
                loop.close()
        
        if result.get("success"):
            logger.info(
                f"Device token {action} in Redis for device {device_dict.get('device_id')}"
            )
        else:
            logger.warning(
                f"Device token sync failed for device {device_dict.get('device_id')}: "
                f"{result.get('message', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(
            f"Error syncing device token to Redis for device "
            f"{device_dict.get('device_id', 'unknown')}: {e!s}"
        )


@event.listens_for(Device, "after_insert")
def device_after_insert(mapper, connection, target: Device) -> None:
    """
    Auto-sync device token to Redis after device is created.
    
    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection
        target: Device instance
    """
    try:
        # Only sync if device has push_token and is linked to a user
        # EU-UserApp uses user_id (not user_uuid) and serial_number (not device_id)
        if target.push_token and target.user_id:
            device_dict = {
                "serial_number": target.serial_number,  # Device identifier  
                "push_token": target.push_token,
                "device_type": target.device_type,
                "device_name": target.device_name,
                "platform": target.platform,
                "device_active": target.device_active,
            }
            
            sync_device_token_to_redis(device_dict, str(target.user_id))
            logger.info(f"Device created and synced to Redis: {target.serial_number}")
        else:
            if not target.push_token:
                logger.debug(
                    f"Device {target.serial_number} has no push_token, skipping Redis sync"
                )
            if not target.user_id:
                logger.debug(
                    f"Device {target.serial_number} not linked to user, skipping Redis sync"
                )
                
    except Exception as e:
        logger.error(
            f"Error in device_after_insert for {target.device_id}: {e!s}"
        )


@event.listens_for(Device, "after_update")
def device_after_update(mapper, connection, target: Device) -> None:
    """
    Auto-sync device token to Redis after device is updated.
    
    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection
        target: Device instance
    """
    try:
        # Only sync if device has push_token and is linked to a user
        if target.push_token and target.user_id:
            device_dict = {
                "serial_number": target.serial_number,
                "push_token": target.push_token,
                "device_type": target.device_type,
                "device_name": target.device_name,
                "platform": target.platform,
                "device_active": target.device_active,
            }
            
            sync_device_token_to_redis(device_dict, str(target.user_id))
            logger.info(f"Device updated and synced to Redis: {target.serial_number}")
        else:
            if not target.push_token:
                logger.debug(
                    f"Device {target.serial_number} has no push_token, skipping Redis sync"
                )
            if not target.user_id:
                logger.debug(
                    f"Device {target.serial_number} not linked to user, skipping Redis sync"
                )
                
    except Exception as e:
        logger.error(
            f"Error in device_after_update for {target.device_id}: {e!s}"
        )


@event.listens_for(Device, "after_delete")
def device_after_delete(mapper, connection, target: Device) -> None:
    """
    Auto-remove device token from Redis after device is deleted.
    
    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection  
        target: Device instance
    """
    try:
        # Only remove if device had push_token and was linked to a user
        if target.push_token and target.user_id:
            device_dict = {
                "serial_number": target.serial_number,
                "push_token": target.push_token,
                "device_type": target.device_type,
                "device_name": target.device_name,
                "platform": target.platform,
                "device_active": target.device_active,
            }
            
            # Always remove from Redis on delete
            from app.cache.dependencies import get_sync_redis_client
            
            redis_client = get_sync_redis_client()
            if redis_client:
                redis_service = DeviceTokenRedisService(redis_client)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        redis_service.remove_device_token_from_redis(
                            device_dict, str(target.user_id)
                        )
                    )
                finally:
                    loop.close()
                    
                logger.info(
                    f"Device deleted and token removed from Redis: {target.serial_number}"
                )
        else:
            logger.debug(
                f"Device {target.serial_number} had no push_token or user link, "
                "skipping Redis removal"
            )
            
    except Exception as e:
        logger.error(
            f"Error in device_after_delete for {target.device_id}: {e!s}"
        )


# Event listener registration (called on app startup)
def register_device_events() -> None:
    """Register all device events - call this in app startup"""
    logger.info("Device token sync events registered ✅")
