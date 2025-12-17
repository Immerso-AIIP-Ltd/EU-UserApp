from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from loguru import logger
from redis.asyncio import Redis

from app.cache.dependencies import get_redis_connection
from app.core.constants import SuccessMessages
from app.core.exceptions.exceptions import HealthCheckError
from app.utils.standard_response import standard_response

router = APIRouter()


@router.get("/health")
async def health(
    request: Request,
) -> JSONResponse:
    """
    Checks the health of a project.

    It returns 200 if the project is healthy.
    """

    return standard_response(
        message=SuccessMessages.HEALTH_CHECKUP,
        request=request,
        data={},
    )


@router.get("/redis_health")
async def redis_health(
    request: Request,
    cache_session: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Checks the health of a project.

    It returns 200 if the project is healthy.
    """
    try:
        await cache_session.ping()
    except Exception as e:
        logger.error(e)
        raise HealthCheckError(detail=str(e)) from e

    return standard_response(
        message=SuccessMessages.HEALTH_CHECKUP,
        request=request,
        data={},
    )
