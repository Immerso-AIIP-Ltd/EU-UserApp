import json
import logging
from typing import Any, List, Optional
from redis.asyncio import Redis

logger = logging.getLogger("django")  # Keeping same logger for consistency, or should use "app"? Leaving as is.

async def sadd(redis_client: Redis, key: str, val: str) -> None:
    try:
        await redis_client.sadd(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in sadd: {e}")


async def srem(redis_client: Redis, key: str, val: str) -> None:
    try:
        await redis_client.srem(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in srem: {e}")


async def smembers(redis_client: Redis, key: str) -> List[str]:
    try:
        members = await redis_client.smembers(key)  # type: ignore[misc]
        return [
            val.decode("utf-8") if isinstance(val, bytes) else val for val in members
        ]
    except Exception as e:
        logger.error(f"Error in smembers: {e}")
        return []


async def lpush(redis_client: Redis, key: str, val: str) -> None:
    try:
        await redis_client.lpush(key, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in lpush: {e}")


async def get_list(redis_client: Redis, key: str) -> List[str]:
    try:
        items = await redis_client.lrange(key, 0, -1)  # type: ignore[misc]
        return [val.decode("utf-8") if isinstance(val, bytes) else val for val in items]
    except Exception as e:
        logger.error(f"Error in get_list: {e}")
        return []


async def lrem(redis_client: Redis, key: str, count: int, val: str) -> None:
    try:
        await redis_client.lrem(key, count, val)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error in lrem: {e}")


async def set_dict(
    redis_client: Redis, key: str, val: Any, timeout: Optional[int] = None,
) -> None:
    try:
        if isinstance(val, (dict, list)):
            val = json.dumps(val)
        await redis_client.set(key, val)
        if timeout:
            await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(f"Error in set_dict: {e}")


async def get_val(redis_client: Redis, key: str) -> Optional[str]:
    try:
        val = await redis_client.get(key)
        if val and isinstance(val, bytes):
            return val.decode("utf-8")
        return val
    except Exception as e:
        logger.error(f"Error in get_val: {e}")
        return None


async def set_val(
    redis_client: Redis, key: str, val: str, timeout: Optional[int] = None,
) -> None:
    try:
        await redis_client.set(key, val)
        if timeout:
            await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(f"Error in set_val: {e}")


async def remove_key(redis_client: Redis, key: str) -> None:
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Error in remove_key: {e}")


async def incr_val(redis_client: Redis, key: str) -> None:
    try:
        await redis_client.incr(key)
    except Exception as e:
        logger.error(f"Error in incr_val: {e}")


async def expire_key(redis_client: Redis, key: str, timeout: int) -> None:
    try:
        await redis_client.expire(key, timeout)
    except Exception as e:
        logger.error(f"Error in expire_key: {e}")
