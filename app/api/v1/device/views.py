from typing import Any, Union

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    DeviceInviteRequest,
    DeviceRegisterRequest,
    EncryptedRequest,
)
from app.cache.base import build_cache_key
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    ErrorMessages,
    ProcessParams,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions import (
    CouponExpiredError,
    DeviceAlreadyInvitedError,
    DeviceRegistrationError,
    InvalidCouponError,
    PayloadNotEncryptedError,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.utils import execute_query
from app.utils.security import SecurityService
from app.utils.standard_response import standard_response
from app.utils.validate_headers import (
    validate_headers_without_auth,
    validate_headers_without_x_device_id,
)

router = APIRouter()


@router.post("/invite")
async def invite_device(
    request: Request,
    payload: Union[EncryptedRequest, dict[str, Any]],
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Invite a new device - Enforced Encryption."""

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
        invite_payload = DeviceInviteRequest(**decrypted_payload)
    except Exception as e:
        raise ValidationError(detail=f"Decryption failed: {e!s}") from e

    coupon = await execute_query(
        query=UserQueries.GET_COUPON,
        params={RequestParams.COUPON_ID: invite_payload.coupon_id},
        db_session=db_session,
    )

    if not coupon:
        raise InvalidCouponError

    coupon_data = dict(coupon[0])

    if coupon_data[ProcessParams.IS_CONSUMED] or coupon_data[ProcessParams.IS_EXPIRED]:
        raise CouponExpiredError

    invited = await execute_query(
        query=UserQueries.CHECK_DEVICE_INVITED,
        params={RequestParams.DEVICE_ID: invite_payload.device_id},
        db_session=db_session,
    )

    if invited:
        raise DeviceAlreadyInvitedError

    await execute_query(
        query=UserQueries.UPSERT_DEVICE_INVITE,
        params={
            RequestParams.DEVICE_ID: invite_payload.device_id,
            RequestParams.COUPON_ID: coupon_data[ProcessParams.ID],
        },
        db_session=db_session,
    )
    await db_session.commit()

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        device_id=invite_payload.device_id,
        platform=headers.get(RequestParams.PLATFORM),
        version=headers.get(RequestParams.APP_VERSION),
        country=headers.get(RequestParams.COUNTRY),
    )
    await cache.delete(cache_key)

    response_data = {
        RequestParams.DEVICE_ID: invite_payload.device_id,
        RequestParams.COUPON_ID: invite_payload.coupon_id,
    }

    return standard_response(
        message=SuccessMessages.DEVICE_INVITED,
        request=request,
        data=response_data,
    )


@router.post("/device_registration")
async def register_device(
    request: Request,
    payload: Union[EncryptedRequest, dict[str, Any]],
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_x_device_id),
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
        await execute_query(
            query=UserQueries.REGISTER_DEVICE,
            params={
                RequestParams.DEVICE_ID: reg_payload.device_id,
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
            },
            db_session=db_session,
        )

        await db_session.commit()
    except Exception as e:

        raise DeviceRegistrationError(
            detail=f"{ErrorMessages.DEVICE_REGISTRATION_FAILED}: {e!s}",
        ) from e

    return standard_response(
        message=SuccessMessages.DEVICE_REGISTERED_SUCCESS,
        request=request,
        data={RequestParams.DEVICE_ID: reg_payload.device_id},
    )
