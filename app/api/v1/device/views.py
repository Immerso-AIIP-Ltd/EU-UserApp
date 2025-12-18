from uuid import UUID
from app.api.v1.schemas import DeviceInviteResponse
from fastapi import APIRouter, Request, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.api.queries import UserQueries
from app.utils.standard_response import standard_response
from app.cache.base import build_cache_key, get_cache, query_hash, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions.exceptions import CategoriesNotFoundError, GamesNotFoundError, ValidationError
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform
from app.utils.standard_response import standard_response
from app.utils.validate_headers import CommonHeaders, validate_common_headers

router = APIRouter()


@router.get("/{device_id}")
async def check_device_invite_status(device_id: str):
    """
    Check Device Invite Status
    """
    return standard_response(
        message="Device invite checked",
        data={"device_id": device_id, "status": "invited"},
    )

@router.get("/{device_id}")
async def check_device_invite_status(
    request: Request,
    device_id: UUID = Path(..., description="Unique device identifier"),
    db_session: AsyncSession = Depends(get_db_session),
    headers: CommonHeaders = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Check whether a device is already invited using device_id."""
    
    # Validate device_id
    if not device_id or not device_id.strip():
        raise ValidationError(
            detail="device_id is required",
            error_code="US400",
            error_type="Validation Error",
            error_details="Query parameter device_id is missing."
        )
    
    params = {"device_id": device_id}
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE,
        **{
            "device_id": device_id,
            RequestParams.X_PLATFORM: headers.platform,
            RequestParams.X_VERSION: headers.version,
            RequestParams.X_APPNAME: headers.appname,
        },
    )
    
    # Check cache
    cached_data = await get_cache(cache, cache_key)
    if cached_data:
        message = SuccessMessages.DEVICE_INVITED if cached_data else SuccessMessages.DEVICE_NOT_INVITED
        return standard_response(
            message=message,
            request=request,
            data=cached_data,
        )
    
    # Query database
    data = await execute_and_transform(
        query=UserQueries.CHECK_DEVICE_INVITE,
        params=params,
        model_class=DeviceInviteResponse,
        db_session=db_session,
    )
    
    # Prepare response
    if data and len(data) > 0:
        device_data = data[0]
        message = SuccessMessages.DEVICE_INVITED
        response_data = {
            "device_id": device_data.device_id,
            "coupon_id": device_data.coupon_id
        }
    else:
        message = SuccessMessages.DEVICE_NOT_INVITED
        response_data = {}
    
    # Cache the result
    await set_cache(
        cache, 
        cache_key, 
        response_data, 
        ttl=CacheTTL.CACHE_TTL_DEVICE_INVITE
    )
    
    return standard_response(
        message=message,
        request=request,
        data=response_data,
    )

@router.post("/invite")
async def invite_device_using_coupon():
    """
    Invite Device Using Coupon
    """
    return standard_response(message="Device invited", data={"status": "success"})
