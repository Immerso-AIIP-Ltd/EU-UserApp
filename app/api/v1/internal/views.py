from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.v1.schemas import CacheStats
from app.cache.dependencies import get_redis_connection
from app.core.constants import Description
from app.core.exceptions.exceptions import CacheConnectionError
from app.utils.standard_response import standard_response

router = APIRouter()


@router.post("/cache/flush")
async def flush_cache(
    request: Request,
    cache_session: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Flush Redis cache.

    - scope = "db": flushes current Redis database (FLUSHDB)
    - scope = "all": flushes all databases (FLUSHALL)
    """

    try:
        await cache_session.flushdb()
        message = Description.CACHE_FLUSH_DB

        return standard_response(
            message=message,
            request=request,
            data={},
        )
    except Exception as e:
        raise CacheConnectionError(detail=str(e)) from e

@router.post("/cache/flush/pattern")
async def flush_cache_by_pattern(
    request: Request,
    pattern: str = Query(
        ...,
        description=Description.REDIS_KEY_PATTERN,
    ),
    cache_session: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Flush Redis cache keys by pattern."""
    try:
        keys = await cache_session.keys(pattern)
        if keys:
            await cache_session.delete(*keys)
        return standard_response(
            message=f"Flushed {len(keys)} keys matching pattern '{pattern}'",
            request=request,
            data={"deleted_keys": len(keys)},
        )
    except Exception as e:
        raise CacheConnectionError(detail=str(e)) from e


@router.delete("/cache/{cache_key}")
async def delete_cache_key(
    request: Request,
    cache_key: str = Path(..., description=Description.REDIS_CACHE_KEY),
    cache_session: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Delete a specific cache key."""
    try:
        deleted = await cache_session.delete(cache_key)
        message = (
            f"Deleted cache key '{cache_key}'"
            if deleted
            else f"Key '{cache_key}' not found"
        )
        return standard_response(
            message=message,
            request=request,
            data={"deleted": bool(deleted)},
        )
    except Exception as e:
        raise CacheConnectionError(detail=str(e)) from e


@router.get("/cache/stats")
async def get_cache_stats(
    request: Request,
    cache_session: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Retrieve Redis cache statistics."""
    try:
        info = await cache_session.info()
        keys = await cache_session.keys("*")

        stats = CacheStats(
            used_memory_human=info.get("used_memory_human"),
            connected_clients=info.get("connected_clients"),
            total_commands_processed=info.get("total_commands_processed"),
            uptime_in_days=info.get("uptime_in_days"),
            total_keys=len(keys),
            keys=[k.decode("utf-8") if isinstance(k, bytes) else k for k in keys],
        )

        return standard_response(
            message=Description.CACHE_STATS_RETRIEVED,
            request=request,
            data=stats.model_dump(),
        )

    except Exception as e:
        raise CacheConnectionError(detail=str(e)) from e
