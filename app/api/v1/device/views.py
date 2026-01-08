from typing import Any

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    DeviceInviteData,
    DeviceInviteRequest,
)
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    ProcessParams,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    DeviceNotInvitedError,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform, execute_query
from app.utils.standard_response import standard_response
from app.utils.validate_headers import validate_headers_without_auth

router = APIRouter()


@router.get("/{device_id}")
async def check_device_invite_status(
    request: Request,
    device_id: str = Path(...),
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Check if a device has been invited."""
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        device_id=device_id,
        platform=headers.get(RequestParams.PLATFORM),
        version=headers.get(RequestParams.APP_VERSION),
        country=headers.get(RequestParams.COUNTRY),
    )

    cached_data = await get_cache(cache, cache_key)
    if cached_data:
        return standard_response(
            message=SuccessMessages.DEVICE_ALREADY_INVITED,
            request=request,
            data=cached_data,
        )

    data = await execute_and_transform(
        query=UserQueries.CHECK_DEVICE_INVITE_STATUS,
        params={RequestParams.DEVICE_ID: device_id},
        model_class=DeviceInviteData,
        db_session=db_session,
    )

    if not data or data[0].get(RequestParams.COUPON_ID) is None:
        raise DeviceNotInvitedError(detail=ErrorMessages.DEVICE_NOT_INVITED)

    await set_cache(cache, cache_key, data, CacheTTL.TTL_INVITE_DEVICE)

    return standard_response(
        message=SuccessMessages.DEVICE_ALREADY_INVITED,
        request=request,
        data=data,
    )


@router.post("/invite")
async def invite_device(
    request: Request,
    payload: DeviceInviteRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Invite a device using a coupon code."""
    coupon = await execute_query(
        query=UserQueries.GET_COUPON,
        params={RequestParams.COUPON_ID: payload.coupon_id},
        db_session=db_session,
    )

    if not coupon:
        raise ValidationError(ErrorMessages.COUPON_ID_INVALID)

    coupon_data = dict(coupon[0])

    if coupon_data[ProcessParams.IS_CONSUMED] or coupon_data[ProcessParams.IS_EXPIRED]:
        raise ValidationError(ErrorMessages.COUPON_EXPIRED)

    invited = await execute_query(
        query=UserQueries.CHECK_DEVICE_INVITED,
        params={RequestParams.DEVICE_ID: payload.device_id},
        db_session=db_session,
    )

    if invited:
        raise ValidationError(ErrorMessages.DEVICE_ALREADY_INVITED)

    await execute_query(
        query=UserQueries.UPSERT_DEVICE_INVITE,
        params={
            RequestParams.DEVICE_ID: payload.device_id,
            RequestParams.COUPON_ID: coupon_data[ProcessParams.ID],
        },
        db_session=db_session,
    )
    await db_session.commit()

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        device_id=payload.device_id,
        platform=headers.get(RequestParams.PLATFORM),
        version=headers.get(RequestParams.APP_VERSION),
        country=headers.get(RequestParams.COUNTRY),
    )
    await cache.delete(cache_key)

    response_data = {
        RequestParams.DEVICE_ID: payload.device_id,
        RequestParams.COUPON_ID: payload.coupon_id,
    }
    return standard_response(
        message=SuccessMessages.DEVICE_INVITED,
        request=request,
        data=response_data,
    )
