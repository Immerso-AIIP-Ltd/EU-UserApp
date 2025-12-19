from fastapi import APIRouter, Depends, Path, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    DeviceInviteResponse,
)
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    SuccessMessages,
)
from app.core.exceptions.exceptions import DeviceNotInvited
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform
from app.utils.standard_response import standard_response
from app.utils.validate_headers import CommonHeaders, validate_common_headers

router = APIRouter()


@router.get("/{device_id}")
async def check_device_invite_status(
    request: Request,
    device_id: str = Path(...),
    db_session: AsyncSession = Depends(get_db_session),
    headers: CommonHeaders = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
):
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        device_id=device_id,
        platform=headers.platform,
        version=headers.app_version,
        country=headers.country,
    )

    cached_data = await get_cache(cache, cache_key)
    if cached_data:
        return standard_response(
            message=SuccessMessages.DEVICE_INVITED,
            request=request,
            data=cached_data,
        )

    data = await execute_and_transform(
        query=UserQueries.CHECK_DEVICE_INVITE_STATUS,
        params={"device_id": device_id},
        model_class=DeviceInviteResponse,
        db_session=db_session,
    )
    if not data:
        raise DeviceNotInvited(detail=ErrorMessages.DEVICE_NOT_INVITED)

    await set_cache(cache, cache_key, data, CacheTTL.TTL_INVITE_DEVICE)

    return standard_response(
        message=SuccessMessages.DEVICE_INVITED,
        request=request,
        data=data,
    )
