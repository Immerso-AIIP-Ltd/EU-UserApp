from typing import Any, Union

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    DeviceInviteData,
    DeviceInviteRequest,
    DeviceRegisterRequest,
    EncryptedRequest,
    SyncDeviceTokenRequest,
)
from app.api.v1.service.device_redis_service import DeviceTokenRedisService
from app.api.v1.service.device_service import DeviceService
from app.api.v1.service.geo_service import GeoService
from app.cache.base import build_cache_key, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    ProcessParams,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions import (
    DecryptionFailedError,
    DeviceNotInvitedError,
    DeviceRegistrationError,
    InvalidCouponError,
    PayloadNotEncryptedError,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform, execute_query
from app.utils.security import SecurityService
from app.utils.standard_response import standard_response
from app.utils.validate_headers import (
    validate_common_headers,
    validate_headers_without_auth,
    validate_headers_without_x_device_id,
)

router = APIRouter()


@router.get("/device-invite-status")
async def check_device_invite_status(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Check if a device has been invited."""
    device_id = headers[RequestParams.DEVICE_ID]

    # Check if device is registered
    device_exists = await execute_query(
        query=UserQueries.CHECK_DEVICE_EXISTS,
        params={RequestParams.ID: device_id},
        db_session=db_session,
    )

    if not device_exists:
        raise ValidationError(ErrorMessages.DEVICE_NOT_REGISTERED)

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        device_id=device_id,
        platform=headers.get(RequestParams.PLATFORM),
        version=headers.get(RequestParams.API_VERSION),
        app_version=headers.get(RequestParams.APP_VERSION),
        country=headers.get(RequestParams.COUNTRY),
    )

    data = await execute_and_transform(
        query=UserQueries.CHECK_DEVICE_INVITE_STATUS,
        params={RequestParams.DEVICE_ID: device_id},
        model_class=DeviceInviteData,
        db_session=db_session,
    )

    if not data or data[0].get("coupon_code") is None:
        # Check waitlist
        waitlist_data = await execute_query(
            query=UserQueries.GET_WAITLIST_BY_DEVICE,
            params={RequestParams.DEVICE_ID: device_id},
            db_session=db_session,
        )

        if waitlist_data:
            queue_number = waitlist_data[0].get(RequestParams.QUEUE_NUMBER)
            data = [
                {
                    RequestParams.QUEUE_NUMBER: str(queue_number),
                    RequestParams.IS_VERIFIED: waitlist_data[0].get(
                        RequestParams.IS_VERIFIED,
                    ),
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            ]
            return standard_response(
                message=SuccessMessages.WAITLIST_QUEUE_STATUS.format(
                    queue_number,
                    device_id,
                ),
                request=request,
                data=data,
            )

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
    payload: Union[EncryptedRequest, dict[str, Any]],
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Invite a device using a coupon code - Enforced Encryption."""

    # Validate and parse encrypted payload
    if not isinstance(payload, EncryptedRequest):
        if (
            not isinstance(payload, dict)
            or "key" not in payload
            or "data" not in payload
        ):
            raise PayloadNotEncryptedError
        try:
            payload = EncryptedRequest(**payload)
        except Exception as e:
            raise PayloadNotEncryptedError from e

    # Decrypt payload
    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        invite_data = DeviceInviteRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    # 1. Check if device is registered
    device_exists = await execute_query(
        query=UserQueries.CHECK_DEVICE_EXISTS,
        params={RequestParams.ID: invite_data.device_id},
        db_session=db_session,
    )

    if not device_exists:
        raise ValidationError(ErrorMessages.DEVICE_NOT_REGISTERED)

    # 2. Validate coupon
    coupon = await execute_query(
        query=UserQueries.GET_COUPON,
        params={RequestParams.COUPON_ID: invite_data.coupon_id},
        db_session=db_session,
    )

    if not coupon:
        raise InvalidCouponError

    coupon_data = dict(coupon[0])

    if coupon_data[ProcessParams.IS_CONSUMED] or coupon_data[ProcessParams.IS_EXPIRED]:
        raise ValidationError(ErrorMessages.COUPON_EXPIRED)

    invited = await execute_query(
        query=UserQueries.CHECK_DEVICE_INVITED,
        params={RequestParams.DEVICE_ID: invite_data.device_id},
        db_session=db_session,
    )

    if invited:
        raise ValidationError(ErrorMessages.DEVICE_ALREADY_INVITED)

    # Check if device is in waitlist to get its ID
    waitlist_entry = await execute_query(
        query=UserQueries.GET_WAITLIST_BY_DEVICE,
        params={RequestParams.DEVICE_ID: invite_data.device_id},
        db_session=db_session,
    )

    # Use waitlist ID if exists, otherwise None (will generate new UUID)
    invite_id = waitlist_entry[0].id if waitlist_entry else None

    await execute_query(
        query=UserQueries.UPSERT_DEVICE_INVITE,
        params={
            RequestParams.ID: invite_id,
            RequestParams.DEVICE_ID: invite_data.device_id,
            RequestParams.COUPON_ID: coupon_data[ProcessParams.ID],
        },
        db_session=db_session,
    )

    await db_session.commit()

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        device_id=invite_data.device_id,
        platform=headers.get(RequestParams.PLATFORM),
        version=headers.get(RequestParams.API_VERSION),
        app_version=headers.get(RequestParams.APP_VERSION),
        country=headers.get(RequestParams.COUNTRY),
    )

    await cache.delete(cache_key)

    return standard_response(
        message=SuccessMessages.DEVICE_INVITED,
        request=request,
        data={
            RequestParams.DEVICE_ID: invite_data.device_id,
            RequestParams.COUPON_ID: invite_data.coupon_id,
        },
    )


@router.post("/device_registration")
async def register_device(
    request: Request,
    payload: Union[EncryptedRequest, dict[str, Any]],
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_x_device_id),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Register a new device - Enforced Encryption."""

    if not isinstance(payload, EncryptedRequest):
        if (
            not isinstance(payload, dict)
            or "key" not in payload
            or "data" not in payload
        ):
            raise PayloadNotEncryptedError
        try:
            payload = EncryptedRequest(**payload)
        except Exception as e:
            raise PayloadNotEncryptedError from e

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        reg_payload = DeviceRegisterRequest(**decrypted_payload)
    except Exception as e:
        raise ValidationError(detail=f"Decryption failed: {e!s}") from e

    try:
        country_code = GeoService.get_country_code_by_ip(reg_payload.device_ip or "")

        result = await execute_query(
            query=UserQueries.REGISTER_DEVICE,
            params={
                RequestParams.SERIAL_NUMBER: reg_payload.serial_number,
                RequestParams.DEVICE_NAME: reg_payload.device_name,
                RequestParams.PLATFORM: (
                    reg_payload.platform.value if reg_payload.platform else None
                ),
                RequestParams.DEVICE_TYPE: reg_payload.device_type,
                RequestParams.PUSH_TOKEN: reg_payload.push_token,
                RequestParams.DEVICE_IP: reg_payload.device_ip,
                RequestParams.IS_VPN: reg_payload.is_vpn,
                RequestParams.IS_ANONYMOUS_PROXY: reg_payload.is_anonymous_proxy,
                RequestParams.RESIDENCY_VERIFIED: reg_payload.residency_verified,
                RequestParams.IS_ROOTED: reg_payload.is_rooted,
                RequestParams.IS_JAILBROKEN: reg_payload.is_jailbroken,
                RequestParams.DEVICE_ACTIVE: reg_payload.device_active,
                RequestParams.DRM_TYPE: reg_payload.drm_type,
                RequestParams.HARDWARE_ENCRYPTION: reg_payload.hardware_encryption,
                RequestParams.TRANSACTION_TYPE: reg_payload.transaction_type,
                RequestParams.IS_IP_LEGAL: reg_payload.is_ip_legal,
                RequestParams.NATIVE_TOKEN: reg_payload.native_token,
                RequestParams.DATE_DEACTIVATED: reg_payload.date_deactivated,
                RequestParams.COUNTRY_CODE: country_code,
            },
            db_session=db_session,
        )

        await db_session.commit()
    except Exception as e:

        raise DeviceRegistrationError(
            detail=f"{ErrorMessages.DEVICE_REGISTRATION_FAILED}: {e!s}",
        ) from e

    device_uuid = str(result[0]["id"]) if result else None

    # Cache push_token in Redis (keyed by device_id) so it can be
    # picked up later in verify_otp_register when user_id is available
    if reg_payload.push_token and device_uuid:
        push_cache_key = build_cache_key(
            CacheKeyTemplates.CACHE_KEY_DEVICE_PUSH_TOKEN,
            device_id=device_uuid,
        )
        await set_cache(
            cache,
            push_cache_key,
            reg_payload.push_token,
            ttl=CacheTTL.TTL_DEVICE_PUSH_TOKEN,
        )
        logger.info(
            f"[DEVICE REG] Cached push_token for device {device_uuid}: "
            f"{reg_payload.push_token[:30]}...",
        )

    return standard_response(
        message=SuccessMessages.DEVICE_REGISTERED_SUCCESS,
        request=request,
        data={RequestParams.DEVICE_ID: device_uuid},
    )


@router.post("/sync-token")
async def sync_device_token(
    request: Request,
    payload: SyncDeviceTokenRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Sync FCM/APNs push token for a device - Authenticated endpoint.

    This endpoint allows the mobile app to update the push notification token
    after login or when the token is refreshed by the OS.

    Use Cases:
    1. App gets FCM token after successful login
    2. FCM token refreshed by OS in background
    3. User enables notifications in app settings

    Args:
        payload: Contains push_token and optional device_type
        headers: Must include x-api-token (auth token) and x-device-id

    Returns:
        Success response with sync status
    """
    device_id = headers.get("x_device_id")

    if not device_id:
        raise ValidationError(detail=ErrorMessages.DEVICE_ID_MISSING)

    try:
        # 1. Verify device exists
        device = await DeviceService.get_device(device_id, db_session)

        # 2. Get user_id from device
        user_uuid = device.get("user_uuid")
        if not user_uuid:
            raise ValidationError(detail="Device not linked to any user")

        # 3. Update push_token in database
        await execute_query(
            UserQueries.UPDATE_DEVICE,
            {
                "device_id": device_id,
                "device_type": payload.device_type,
                "device_name": None,
                "push_token": payload.push_token,
            },
            db_session,
        )
        await db_session.commit()

        # 4. Get updated device and sync to Redis
        updated_device = await DeviceService.get_device(device_id, db_session)
        redis_service = DeviceTokenRedisService(cache)
        sync_result = await redis_service.store_device_token_in_redis(
            updated_device,
            str(user_uuid),
        )

        return standard_response(
            message="Device token synced successfully",
            request=request,
            data={
                "device_id": device_id,
                "token_updated": True,
                "redis_synced": sync_result.get("success", False),
            },
        )

    except Exception as e:
        raise ValidationError(detail=f"Failed to sync device token: {e!s}") from e
