import base64
import json
import time
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    DeviceBootstrapRequest,
    DeviceInviteData,
    DeviceInviteRequest,
    DeviceRegisterRequest,
)
from app.api.v1.service.fusionauth_service import FusionAuthService
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    DeviceNames,
    ErrorMessages,
    HTTPStatus,
    ProcessParams,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    BootstrapKeyIdNotConfiguredError,
    DeviceNotInvitedError,
    DeviceRegistrationError,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform, execute_query
from app.settings import settings
from app.utils.standard_response import standard_response
from app.utils.validate_headers import (
    validate_headers_without_auth,
    validate_headers_without_x_device_id,
)

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


@router.post("/device_registration")
async def device_registration(  # noqa: C901
    request: Request,
    payload: DeviceBootstrapRequest,
    db_session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Secure Device Bootstrap.

    Decrypts payload, validates timestamp, and registers/returns device.
    """
    # 1. Fetch Private Key from FusionAuth
    key_id = settings.fusionauth_bootstrap_key_id
    if not key_id:
        # Fallback for dev/testing if not set, or error
        # Assuming we need it
        raise BootstrapKeyIdNotConfiguredError

    try:
        key_obj = FusionAuthService.get_key(key_id)
        private_key_pem = key_obj.get("privateKey")
        if not private_key_pem:
            raise ValidationError(ErrorMessages.PRIVATE_KEY_NOT_FOUND)
    except Exception as e:
        raise ValidationError(f"{ErrorMessages.KEY_RETRIEVAL_FAILED}: {e!s}") from e

    # 2. Decrypt AES Key
    try:
        # Decode Key from Base64
        encrypted_aes_key = base64.b64decode(payload.key)

        # Load Private Key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend(),
        )

        if not isinstance(private_key, (rsa.RSAPrivateKey,)):
            raise ValidationError(ErrorMessages.DECRYPTION_FAILED)

        # RSA Decrypt (assuming OAEP + SHA256 as standard, modify if client differs)
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception as e:
        raise ValidationError(f"{ErrorMessages.DECRYPTION_FAILED}: {e!s}") from e

    # 3. Decrypt Payload
    try:
        encrypted_data = base64.b64decode(payload.data)

        if len(encrypted_data) < 28:  # 12 (IV) + 16 (Tag)
            raise ValidationError(ErrorMessages.INVALID_ENCRYPTED_DATA_LENGTH)

        iv = encrypted_data[:12]
        tag = encrypted_data[-16:]
        ciphertext = encrypted_data[12:-16]

        # Using cryptography.hazmat
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv, tag),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted_payload_bytes = decryptor.update(ciphertext) + decryptor.finalize()

        payload_json = json.loads(decrypted_payload_bytes.decode("utf-8"))

    except Exception as e:
        # Fallback check for CBC?
        raise ValidationError(
            f"{ErrorMessages.PAYLOAD_DECRYPTION_FAILED}: {e!s}",
        ) from e

    # 4. Validate Timestamp
    timestamp = payload_json.get("timestamp")
    if not timestamp:
        raise ValidationError(ErrorMessages.TIMESTAMP_MISSING)

    now = int(time.time())
    if abs(now - int(timestamp)) > 30:
        # 403 Forbidden
        return JSONResponse(
            status_code=HTTPStatus.FORBIDDEN,
            content={"detail": ErrorMessages.REQUEST_EXPIRED},
        )

    install_id = payload_json.get("install_id")
    if not install_id:
        raise ValidationError(ErrorMessages.INSTALL_ID_MISSING)

    # Check existence
    existing = await execute_query(
        query=UserQueries.CHECK_DEVICE_EXISTS,
        params={RequestParams.DEVICE_ID: install_id},
        db_session=db_session,
    )

    if existing:
        # Return existing
        return standard_response(
            message=SuccessMessages.DEVICE_REGISTERED_SUCCESS,
            request=request,
            data={"device_ref": install_id, "status": "REGISTERED"},
        )

    # Create new (Register)
    # Mapping payload fields to Register Request
    try:
        # We might need default values for required fields in REGISTER Device
        # install_id -> device_id
        # platform -> platform

        params = {
            RequestParams.DEVICE_ID: install_id,
            RequestParams.DEVICE_NAME: payload_json.get(
                "device_name",
                DeviceNames.BOOTSTRAP_DEVICE,
            ),
            RequestParams.PLATFORM: payload_json.get("platform"),
            RequestParams.DEVICE_TYPE: payload_json.get("device_type"),
            RequestParams.PUSH_TOKEN: payload_json.get("push_token"),
            RequestParams.DEVICE_IP: payload_json.get("device_ip"),
            RequestParams.IS_VPN: payload_json.get("is_vpn"),
            RequestParams.IS_ANONYMOUS_PROXY: payload_json.get("is_anonymous_proxy"),
            RequestParams.RESIDENCY_VERIFIED: payload_json.get("residency_verified"),
            RequestParams.IS_ROOTED: payload_json.get("is_rooted"),
            RequestParams.IS_JAILBROKEN: payload_json.get("is_jailbroken"),
            RequestParams.DEVICE_ACTIVE: payload_json.get("device_active", True),
            RequestParams.DRM_TYPE: payload_json.get("drm_type"),
            RequestParams.HARDWARE_ENCRYPTION: payload_json.get("hardware_encryption"),
            RequestParams.TRANSACTION_TYPE: payload_json.get("transaction_type"),
            RequestParams.IS_IP_LEGAL: payload_json.get("is_ip_legal"),
            RequestParams.NATIVE_TOKEN: payload_json.get("native_token"),
            RequestParams.DATE_DEACTIVATED: payload_json.get("date_deactivated"),
        }

        await execute_query(
            query=UserQueries.REGISTER_DEVICE,
            params=params,
            db_session=db_session,
        )
        await db_session.commit()

    except Exception as e:
        raise ValidationError(f"{ErrorMessages.DB_ERROR}: {e!s}") from e

    return standard_response(
        message=SuccessMessages.DEVICE_REGISTERED_SUCCESS,
        request=request,
        data={"device_ref": install_id, "status": "REGISTERED"},
    )


@router.post("/register")
async def register_device(
    request: Request,
    payload: DeviceRegisterRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_x_device_id),
) -> JSONResponse:
    """Register a new device."""
    try:
        device_rows = await execute_query(
            query=UserQueries.REGISTER_DEVICE,
            params={
                RequestParams.DEVICE_ID: payload.device_id,
                RequestParams.DEVICE_NAME: payload.device_name,
                RequestParams.PLATFORM: (
                    payload.platform.value if payload.platform else None
                ),
                RequestParams.DEVICE_TYPE: payload.device_type,
                RequestParams.PUSH_TOKEN: payload.push_token,
                RequestParams.DEVICE_IP: payload.device_ip,
                RequestParams.IS_VPN: payload.is_vpn,
                RequestParams.IS_ANONYMOUS_PROXY: payload.is_anonymous_proxy,
                RequestParams.RESIDENCY_VERIFIED: payload.residency_verified,
                RequestParams.IS_ROOTED: payload.is_rooted,
                RequestParams.IS_JAILBROKEN: payload.is_jailbroken,
                RequestParams.DEVICE_ACTIVE: payload.device_active,
                RequestParams.DRM_TYPE: payload.drm_type,
                RequestParams.HARDWARE_ENCRYPTION: payload.hardware_encryption,
                RequestParams.TRANSACTION_TYPE: payload.transaction_type,
                RequestParams.IS_IP_LEGAL: payload.is_ip_legal,
                RequestParams.NATIVE_TOKEN: payload.native_token,
                RequestParams.DATE_DEACTIVATED: payload.date_deactivated,
            },
            db_session=db_session,
        )
        await db_session.commit()
    except Exception as e:

        raise DeviceRegistrationError(
            detail=f"{ErrorMessages.DEVICE_REGISTRATION_FAILED}: {e!s}",
        ) from e

    device_uuid = str(device_rows[0][ProcessParams.ID])

    return standard_response(
        message=SuccessMessages.DEVICE_REGISTERED_SUCCESS,
        request=request,
        data={RequestParams.DEVICE_ID: device_uuid},
    )
