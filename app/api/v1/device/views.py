from datetime import datetime

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import insert, update
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
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    DeviceNotInvited,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.models.user_app import DeviceInvite, InviteCoupon
from app.db.utils import execute_and_transform, execute_query
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
) -> JSONResponse:
    """
    Check if a device has been invited.

    Args:
        request (Request): FastAPI request object.
        device_id (str): UUID of the device to check.
        db_session (AsyncSession): Database session dependency.
        headers (CommonHeaders): Validated headers dependency.
        cache (Redis): Redis cache dependency.

    Returns:
        JSONResponse: Status and device invite details.
    """
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
        model_class=DeviceInviteData,
        db_session=db_session,
    )

    if not data or data[0].get("coupon_id") is None:
        raise DeviceNotInvited(detail=ErrorMessages.DEVICE_NOT_INVITED)

    await set_cache(cache, cache_key, data, CacheTTL.TTL_INVITE_DEVICE)

    return standard_response(
        message=SuccessMessages.DEVICE_INVITED,
        request=request,
        data=data,
    )


@router.post("/invite")
async def invite_device(
    request: Request,
    payload: DeviceInviteRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: CommonHeaders = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Invite a device using a coupon or invitation.

    Args:
        request (Request): FastAPI request object.
        payload (DeviceInviteRequest): Data required to invite a device.
        db_session (AsyncSession): Database session dependency.
        headers (CommonHeaders): Validated headers dependency.
        cache (Redis): Redis cache dependency.

    Returns:
        JSONResponse: Status of the invitation and related data.
    """
    coupon = await execute_query(
        query=UserQueries.GET_COUPON,
        params={"coupon_id": payload.coupon_id},
        db_session=db_session,
    )

    if not coupon:
        raise ValidationError(ErrorMessages.COUPON_ID_INVALID)

    coupon = coupon[0]

    if coupon["is_consumed"] or coupon["is_expired"]:
        raise ValidationError(ErrorMessages.COUPON_EXPIRED)

    invited = await execute_query(
        query=UserQueries.CHECK_DEVICE_INVITED,
        params={"device_id": payload.device_id},
        db_session=db_session,
    )

    if invited:
        raise ValidationError(ErrorMessages.DEVICE_ALREADY_INVITED)

    async with db_session.begin():
        await db_session.execute(
            insert(DeviceInvite).values(
                device_id=payload.device_id,
                coupon_id=coupon["id"],
                created_at=datetime.utcnow(),
            ),
        )
        await db_session.execute(
            update(InviteCoupon)
            .where(InviteCoupon.id == coupon["id"])
            .where(InviteCoupon.consumed_at.is_(None))
            .values(consumed_at=datetime.utcnow()),
        )

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        device_id=payload.device_id,
        platform=headers.platform,
        version=headers.app_version,
        country=headers.country,
    )
    await cache.delete(cache_key)

    return standard_response(
        message=SuccessMessages.DEVICE_INVITED,
        request=request,
        data={
            "device_id": payload.device_id,
            "coupon_id": payload.coupon_id,
        },
    )
