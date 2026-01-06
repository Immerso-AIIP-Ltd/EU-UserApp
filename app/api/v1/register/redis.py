import json
import logging
from typing import Any, List, Optional

from redis.asyncio import Redis

from app.core.constants import LoginParams, RedisLogMessages

logger = logging.getLogger("django")


async def remove_uuid_device_token(
    redis_client: Redis,
    uuid: str,
    platform: str,
    device_token: str,
) -> None:
    """Remove a specific device token for a user (UUID) from Redis."""
    try:
        current_data = await redis_client.get(str(uuid))
        if current_data:
            if isinstance(current_data, bytes):
                current_data = current_data.decode(LoginParams.UTF8)

            data = json.loads(current_data)
            if platform in data:
                tokens = data[platform]
                if device_token in tokens:
                    tokens.remove(device_token)
                    data[platform] = tokens
                    await redis_client.set(str(uuid), json.dumps(data))
    except Exception as e:
        logger.error(RedisLogMessages.REMOVE_DEVICE_TOKEN_ERROR.format(e))


async def save_device_token(
    redis_client: Redis,
    device_id: str,
    device_token: str,
    timeout: Optional[int] = None,
) -> None:
    """Save a device token mapping for a specific device ID."""
    try:
        if timeout:
            await redis_client.set(device_id, device_token, ex=timeout)
        else:
            await redis_client.set(device_id, device_token)
    except Exception as e:
        logger.error(RedisLogMessages.SAVE_DEVICE_TOKEN_ERROR.format(e))


async def add_uuid_device_token(
    redis_client: Redis,
    uuid: str,
    platform: str,
    device_token: str,
    timeout: Optional[int] = None,
) -> None:
    """Add a new device token to the list of tokens for a user (UUID)."""
    try:
        current_data = await redis_client.get(str(uuid))
        data = {}
        if current_data:
            if isinstance(current_data, bytes):
                current_data = current_data.decode(LoginParams.UTF8)
            data = json.loads(current_data)

        if platform not in data:
            data[platform] = []

        if device_token not in data[platform]:
            data[platform].append(device_token)
            await redis_client.set(str(uuid), json.dumps(data))

        if timeout:
            await redis_client.expire(str(uuid), timeout)

    except Exception as e:
        logger.error(RedisLogMessages.ADD_DEVICE_TOKEN_ERROR.format(e))


async def sadd(redis_client: Redis, key: str, val: str) -> None:
    """Add a member to a set in Redis."""
    try:
        await redis_client.sadd(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(RedisLogMessages.SADD_ERROR.format(e))


async def srem(redis_client: Redis, key: str, val: str) -> None:
    """Remove a member from a set in Redis."""
    try:
        await redis_client.srem(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(RedisLogMessages.SREM_ERROR.format(e))


async def smembers(redis_client: Redis, key: str) -> List[str]:
    """Return all members of a set in Redis."""
    try:
        members = await redis_client.smembers(key)  # type: ignore[misc]
        return [
            val.decode(LoginParams.UTF8) if isinstance(val, bytes) else val
            for val in members
        ]
    except Exception as e:
        logger.error(RedisLogMessages.SMEMBERS_ERROR.format(e))
        return []


async def lpush(redis_client: Redis, key: str, val: str) -> None:
    """Push a value to the head of a list in Redis."""
    try:
        await redis_client.lpush(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(RedisLogMessages.LPUSH_ERROR.format(e))


async def get_list(redis_client: Redis, key: str) -> List[str]:
    """Retrieve all items from a list in Redis."""
    try:
        items = await redis_client.lrange(key, 0, -1)  # type: ignore[misc]
        return [
            val.decode(LoginParams.UTF8) if isinstance(val, bytes) else val
            for val in items
        ]
    except Exception as e:
        logger.error(RedisLogMessages.GET_LIST_ERROR.format(e))
        return []


async def lrem(redis_client: Redis, key: str, count: int, val: str) -> None:
    """Remove occurrences of a value from a list in Redis."""
    try:
        await redis_client.lrem(key, count, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(RedisLogMessages.LREM_ERROR.format(e))


async def set_dict(
    redis_client: Redis,
    key: str,
    val: Any,
    timeout: Optional[int] = None,
) -> None:
    """Save a dictionary or list as a JSON string in Redis."""
    try:
        if isinstance(val, (dict, list)):
            val = json.dumps(val)
        await redis_client.set(key, val)
        if timeout:
            await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(RedisLogMessages.SET_DICT_ERROR.format(e))


async def get_val(redis_client: Redis, key: str) -> Optional[str]:
    """Retrieve a string value from Redis."""
    try:
        val = await redis_client.get(key)
        if val and isinstance(val, bytes):
            return val.decode(LoginParams.UTF8)
        return val
    except Exception as e:
        logger.error(RedisLogMessages.GET_VAL_ERROR.format(e))
        return None


async def set_val(
    redis_client: Redis,
    key: str,
    val: str,
    timeout: Optional[int] = None,
) -> None:
    """Save a string value to Redis with an optional timeout."""
    try:
        await redis_client.set(key, val)
        if timeout:
            await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(RedisLogMessages.SET_VAL_ERROR.format(e))


async def remove_key(redis_client: Redis, key: str) -> None:
    """Delete a key from Redis."""
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(RedisLogMessages.REMOVE_KEY_ERROR.format(e))


async def incr_val(redis_client: Redis, key: str) -> None:
    """Increment the integer value of a key in Redis."""
    try:
        await redis_client.incr(key)
    except Exception as e:
        logger.error(RedisLogMessages.INCR_VAL_ERROR.format(e))


async def expire_key(redis_client: Redis, key: str, timeout: int) -> None:
    """Set an expiration timeout on a Redis key."""
    try:
        await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(RedisLogMessages.EXPIRE_KEY_ERROR.format(e))
