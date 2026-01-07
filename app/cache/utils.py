import json
import logging
from typing import Any, List, Optional

from redis.asyncio import Redis

logger = logging.getLogger(
    "django",
)  # Keeping same logger for consistency, or should use "app"? Leaving as is.


async def sadd(redis_client: Redis, key: str, val: str) -> None:
    """Add a member to a set in Redis."""
    try:
        await redis_client.sadd(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in sadd: {e}")


async def srem(redis_client: Redis, key: str, val: str) -> None:
    """Remove a member from a set in Redis."""
    try:
        await redis_client.srem(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in srem: {e}")


async def smembers(redis_client: Redis, key: str) -> List[str]:
    """Get all members of a set in Redis."""
    try:
        members = await redis_client.smembers(key)  # type: ignore[misc]
        return [
            val.decode("utf-8") if isinstance(val, bytes) else val for val in members
        ]
    except Exception as e:
        logger.error(f"Error in smembers: {e}")
        return []


async def lpush(redis_client: Redis, key: str, val: str) -> None:
    """Push a value to the beginning of a list in Redis."""
    try:
        await redis_client.lpush(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in lpush: {e}")


async def get_list(redis_client: Redis, key: str) -> List[str]:
    """Get all items from a list in Redis."""
    try:
        items = await redis_client.lrange(key, 0, -1)  # type: ignore[misc]
        return [val.decode("utf-8") if isinstance(val, bytes) else val for val in items]
    except Exception as e:
        logger.error(f"Error in get_list: {e}")
        return []


async def lrem(redis_client: Redis, key: str, count: int, val: str) -> None:
    """Remove occurrences of a value from a list in Redis."""
    try:
        await redis_client.lrem(key, count, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in lrem: {e}")


async def set_dict(
    redis_client: Redis,
    key: str,
    val: Any,
    timeout: Optional[int] = None,
) -> None:
    """Set a dictionary or list as a JSON string in Redis with an optional timeout."""
    try:
        if isinstance(val, (dict, list)):
            val = json.dumps(val)
        await redis_client.set(key, val)
        if timeout:
            await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(f"Error in set_dict: {e}")


async def get_val(redis_client: Redis, key: str) -> Optional[str]:
    """Retrieve a string value from Redis by key."""
    try:
        val = await redis_client.get(key)
        if val and isinstance(val, bytes):
            return val.decode("utf-8")
        return val
    except Exception as e:
        logger.error(f"Error in get_val: {e}")
        return None


async def set_val(
    redis_client: Redis,
    key: str,
    val: str,
    timeout: Optional[int] = None,
) -> None:
    """Set a string value in Redis with an optional timeout."""
    try:
        await redis_client.set(key, val)
        if timeout:
            await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(f"Error in set_val: {e}")


async def remove_key(redis_client: Redis, key: str) -> None:
    """Delete a key from Redis."""
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Error in remove_key: {e}")


async def incr_val(redis_client: Redis, key: str) -> None:
    """Increment the integer value of a key in Redis."""
    try:
        await redis_client.incr(key)
    except Exception as e:
        logger.error(f"Error in incr_val: {e}")


async def expire_key(redis_client: Redis, key: str, timeout: int) -> None:
    """Set a timeout on a key in Redis."""
    try:
        await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(f"Error in expire_key: {e}")
