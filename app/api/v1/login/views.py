import logging
from datetime import datetime, timedelta
from typing import Any, Sequence

import jwt
import pytz  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    ChangePasswordRequest,
    EncryptedRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    SetForgotPasswordRequest,
    UserProfileData,
)
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.change_password_service import ChangePasswordService
from app.api.v1.service.device_service import DeviceService
from app.api.v1.service.forgot_password_service import ForgotPasswordService
from app.api.v1.service.login_service import LoginService
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    AuthConfig,
    ErrorMessages,
    HeaderKeys,
    ProcessParams,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions import (
    DecryptionFailedError,
    DeviceNotRegisteredError,
    EmailMobileRequiredError,
    InvalidInputError,
    UserNotFoundError,
)
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform, execute_query
from app.settings import settings
from app.utils.security import SecurityService
from app.utils.standard_response import standard_response
from app.utils.validate_headers import (
    validate_common_headers,
    validate_headers_without_auth,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login")
async def login_user(
    request: Request,
    payload: EncryptedRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Authenticate user using Encrypted or Plain JSON (for Testing)."""

    if isinstance(payload, EncryptedRequest):
        try:
            decrypted_payload = SecurityService.decrypt_payload(
                encrypted_key=payload.key,
                encrypted_data=payload.data,
            )
            login_data = LoginRequest(**decrypted_payload)
        except Exception as e:
            raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e
    else:
        login_data = payload

    device_id = headers.get(HeaderKeys.X_DEVICE_ID) or headers.get(HeaderKeys.DEVICE_ID)
    client_id = headers.get(HeaderKeys.X_API_CLIENT) or headers.get(
        HeaderKeys.API_CLIENT,
    )
    # 0. Bypass for load tests
    if (
        request.headers.get(HeaderKeys.X_LOAD_TEST_BYPASS)
        == settings.load_test_bypass_secret
    ):
        # Fetch actual user
        user_rows: Sequence[RowMapping] = []
        if login_data.email:
            user_rows = await execute_query(
                UserQueries.GET_USER_BY_EMAIL,
                {RequestParams.EMAIL: login_data.email},
                db_session,
            )
        elif login_data.mobile:
            user_rows = await execute_query(
                UserQueries.GET_USER_BY_MOBILE,
                {
                    RequestParams.MOBILE: login_data.mobile,
                    RequestParams.CALLING_CODE: login_data.calling_code,
                },
                db_session,
            )

        if not user_rows:
            raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND_BYPASS)

        user_data = user_rows[0]
        user_id = user_data["id"]

        # Use settings for secret
        secret = settings.jwt_secret_key
        expiry = datetime.now(pytz.utc) + timedelta(
            days=settings.user_token_days_to_expire,
        )

        token_payload = {RequestParams.UUID: str(user_id), RequestParams.EXP: expiry}

        token = jwt.encode(
            token_payload,
            secret,
            algorithm=AuthConfig.ALGORITHM,
        )

        return standard_response(
            message=SuccessMessages.USER_LOGGED_IN,
            request=request,
            data={
                RequestParams.AUTH_TOKEN: token,
                RequestParams.USER: {
                    RequestParams.USER_ID: str(user_id),
                    RequestParams.EMAIL: user_data.get("email"),
                    RequestParams.NAME: "Load Test User",
                },
            },
        )

    # 1. Login via service
    user, token, refresh_token, expires_at = await LoginService.login_user(
        login_data=login_data,
        client_id=client_id,
        device_id=device_id,
        db_session=db_session,
        cache=cache,
    )

    # 2. Fetch Full Profile for response
    profile_data_list = await execute_and_transform(
        UserQueries.GET_USER_PROFILE,
        {RequestParams.USER_ID: user[ProcessParams.ID]},
        UserProfileData,
        db_session,
    )

    profile = (
        profile_data_list[0]
        if profile_data_list
        else {
            RequestParams.USER_ID: str(user[ProcessParams.ID]),
            RequestParams.EMAIL: user.get(RequestParams.EMAIL),
            RequestParams.NAME: user.get(RequestParams.NAME),
        }
    )

    # 3. Format response
    user_response = {
        RequestParams.USER_ID: str(user[ProcessParams.ID]),
        RequestParams.EMAIL: profile.get(RequestParams.EMAIL),
        RequestParams.NAME: profile.get(RequestParams.NAME),
        RequestParams.IMAGE: profile.get(RequestParams.IMAGE),
    }

    response_data = {
        RequestParams.AUTH_TOKEN: token,
        RequestParams.REFRESH_TOKEN: refresh_token,
        RequestParams.USER: user_response,
    }

    return standard_response(
        message=SuccessMessages.USER_LOGGED_IN,
        request=request,
        data=response_data,
    )


@router.post("/forgot_password")
async def forgot_password(
    request: Request,
    payload: EncryptedRequest,
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    db: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Forgot password handler using Encrypted email or mobile."""

    # 0. Check if device is registered
    device_id = headers.get(HeaderKeys.X_DEVICE_ID) or headers.get(HeaderKeys.DEVICE_ID)
    if not device_id or not await DeviceService.is_device_registered(
        device_id,
        db,
    ):
        raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        forgot_payload = ForgotPasswordRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    # Validate email or mobile
    if not forgot_payload.validate_email_or_mobile():
        raise EmailMobileRequiredError

    ip = request.client.host if request.client else "unknown"

    # Selecting email or mobile flow
    if forgot_payload.email:
        message = await ForgotPasswordService.forgot_password_email(
            db,
            forgot_payload.email,
            cache,
        )
    else:
        message = await ForgotPasswordService.forgot_password_mobile(
            db,
            forgot_payload.mobile or "",
            forgot_payload.calling_code or "",
            ip,
            cache,
        )

    data: dict[str, Any] = {}
    return standard_response(
        message=message,
        request=request,
        data=data,
    )


@router.post("/set_forgot_password")
async def set_forgot_password(
    request: Request,
    payload: EncryptedRequest,
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    db: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Set new password after OTP verification (Encrypted)."""

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        set_forgot_payload = SetForgotPasswordRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    device_id = headers.get(HeaderKeys.X_DEVICE_ID) or headers.get(HeaderKeys.DEVICE_ID)
    client_id = headers.get(HeaderKeys.X_API_CLIENT) or headers.get(
        HeaderKeys.API_CLIENT,
    )

    token, refresh_token, expires_at = await ForgotPasswordService.set_forgot_password(
        db=db,
        email=str(set_forgot_payload.email),
        password=set_forgot_payload.password,
        client_id=str(client_id),
        device_id=str(device_id),
        cache=cache,
    )

    response_data = {
        RequestParams.AUTH_TOKEN: token,
        RequestParams.REFRESH_TOKEN: refresh_token,
        RequestParams.AUTH_TOKEN_EXPIRY: expires_at,
    }

    return standard_response(
        message=SuccessMessages.PASSWORD_RESET_SUCCESS,
        request=request,
        data=response_data,
    )


@router.put("/change_password")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    headers: dict[str, Any] = Depends(validate_common_headers),
    db_session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Change user password.

    Requires valid x-api-token in headers.
    """
    # 1. Get user UUID from token
    user_id = await AuthService.verify_user_token(headers, db_session)

    # 2. Call service
    await ChangePasswordService.change_password(
        user_uuid=user_id,
        new_password=payload.new_password,
        new_password_confirm=payload.new_password_confirm,
        db_session=db_session,
    )

    data: dict[str, Any] = {}
    return standard_response(
        message=SuccessMessages.PASSWORD_CHANGED_SUCCESS,
        request=request,
        data=data,
    )


@router.post("/refresh_token")
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
) -> JSONResponse:
    """Refresh access token using refresh token."""
    device_id = headers.get(HeaderKeys.X_DEVICE_ID) or headers.get(HeaderKeys.DEVICE_ID)

    if not device_id:
        raise InvalidInputError(ErrorMessages.DEVICE_ID_MISSING)

    token, new_refresh_token, expires_at = await AuthService.refresh_access_token(
        db_session=db_session,
        refresh_token=payload.refresh_token,
        device_id=device_id,
    )

    response_data = {
        RequestParams.AUTH_TOKEN: token,
        RequestParams.REFRESH_TOKEN: new_refresh_token,
        RequestParams.AUTH_TOKEN_EXPIRY: expires_at,
    }

    return standard_response(
        message=SuccessMessages.TOKEN_REFRESHED_SUCCESSFULLY,
        request=request,
        data=response_data,
    )
