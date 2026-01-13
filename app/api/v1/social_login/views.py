from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    EncryptedRequest,
    FacebookLoginRequest,
    SocialLoginRequest,
)
from app.api.v1.service.apple_oauth_service import AppleOAuthService
from app.api.v1.service.facebook_oauth_service import FacebookOAuthService
from app.api.v1.service.google_oauth_service import GoogleOAuthService
from app.api.v1.service.social_login_service import SocialLoginService
from app.cache.dependencies import get_redis_connection
from app.core.constants import SuccessMessages
from app.core.exceptions import DecryptionFailedError
from app.db.dependencies import get_db_session
from app.utils.security import SecurityService
from app.utils.standard_response import standard_response
from app.utils.validate_headers import validate_headers_without_auth

router = APIRouter()


@router.post("/google_login")
async def google_login(
    request: Request,
    payload: EncryptedRequest,
    db_session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
) -> JSONResponse:
    """Google Login / Sign Up API (Encrypted)."""

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        login_data = SocialLoginRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    google_service = GoogleOAuthService(
        login_data.id_token,
        headers.get("platform") or "unknown",
    )

    request_data = {
        "uid": login_data.uid,
        "client_id": headers.get("api_client"),
        "device_id": headers.get("device_id"),
        "platform": headers.get("platform"),
        "country": headers.get("country"),
        "user_agent": request.headers.get("User-Agent"),
    }
    data = await SocialLoginService.google_login(
        google_service=google_service,
        request_data=request_data,
        db_session=db_session,
        cache=cache,
    )
    return standard_response(
        message=SuccessMessages.USER_LOGGED_IN,
        request=request,
        data=data,
    )


@router.post("/apple_login")
async def apple_login(
    request: Request,
    payload: EncryptedRequest,
    db_session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
) -> JSONResponse:
    """Apple Login / Sign Up API (Encrypted)."""

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        login_data = SocialLoginRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    apple_service = AppleOAuthService(
        login_data.id_token,
        headers.get("platform") or "unknown",
    )

    request_data = {
        "uid": login_data.uid,
        "client_id": headers.get("api_client"),
        "device_id": headers.get("device_id"),
        "platform": headers.get("platform"),
        "country": headers.get("country"),
        "user_agent": request.headers.get("User-Agent"),
    }

    data = await SocialLoginService.apple_login(
        apple_service=apple_service,
        request_data=request_data,
        db_session=db_session,
        cache=cache,
    )

    return standard_response(
        message=SuccessMessages.USER_LOGGED_IN,
        request=request,
        data=data,
    )


@router.post("/facebook_login")
async def facebook_login(
    request: Request,
    payload: EncryptedRequest,
    db_session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
) -> JSONResponse:
    """Facebook Login / Sign Up API (Encrypted)."""

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        login_data = FacebookLoginRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    facebook_service = FacebookOAuthService(login_data.access_token)
    request_data = {
        "uid": login_data.uid,
        "client_id": headers.get("api_client"),
        "device_id": headers.get("device_id"),
        "platform": headers.get("platform"),
        "country": headers.get("country"),
        "user_agent": request.headers.get("User-Agent"),
    }
    data = await SocialLoginService.facebook_login(
        facebook_service=facebook_service,
        request_data=request_data,
        db_session=db_session,
        cache=cache,
    )

    return standard_response(
        message=SuccessMessages.USER_LOGGED_IN,
        request=request,
        data=data,
    )
