from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    SetForgotPasswordRequest,
    UserProfileData,
)
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.change_password_service import ChangePasswordService
from app.api.v1.service.forgot_password_service import ForgotPasswordService
from app.api.v1.service.login_service import LoginService
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    HeaderKeys,
    Messages,
    ProcessParams,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions import InvalidInputError
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform
from app.utils.standard_response import standard_response
from app.utils.validate_headers import (
    validate_common_headers,
    validate_headers_without_auth,
)

router = APIRouter()


@router.post("/login")
async def login_user(
    request: Request,
    login_data: LoginRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Authenticate user using Email or Mobile and Password."""
    device_id = headers.get(HeaderKeys.X_DEVICE_ID) or headers.get(HeaderKeys.DEVICE_ID)
    client_id = headers.get(HeaderKeys.X_API_CLIENT) or headers.get(
        HeaderKeys.API_CLIENT,
    )

    # 1. Login via service
    user, token, expires_at = await LoginService.login_user(
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
        RequestParams.AUTH_TOKEN_EXPIRY: expires_at,
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
    payload: ForgotPasswordRequest,
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    db: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Forgot password handler using email or mobile.

    Common headers are validated through validate_common_headers().
    """

    # Validate email or mobile
    if not payload.validate_email_or_mobile():
        raise InvalidInputError(Messages.EMAIL_OR_MOBILE_REQUIRED)

    ip = request.client.host if request.client else "unknown"

    # Selecting email or mobile flow
    if payload.email:
        message = await ForgotPasswordService.forgot_password_email(
            db,
            payload.email,
            cache,
        )
    else:
        message = await ForgotPasswordService.forgot_password_mobile(
            db,
            payload.mobile or "",
            payload.calling_code or "",
            ip,
            cache,
        )

    data: dict[str, Any] = {}
    return standard_response(
        message=message,
        request=request,
        data=data,
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
    # validate_common_headers confirms presence, but does not verify. We verify here.
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


@router.post("/set_forgot_password")
async def set_forgot_password(
    request: Request,
    payload: SetForgotPasswordRequest,
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    db: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Set new password after OTP verification."""
    device_id = headers.get(HeaderKeys.X_DEVICE_ID) or headers.get(HeaderKeys.DEVICE_ID)
    client_id = headers.get(HeaderKeys.X_API_CLIENT) or headers.get(
        HeaderKeys.API_CLIENT,
    )

    token, expires_at = await ForgotPasswordService.set_forgot_password(
        db=db,
        email=str(payload.email),
        password=payload.password,
        client_id=str(client_id),
        device_id=str(device_id),
        cache=cache,
    )

    response_data = {
        "auth_token": token,
        "token": "",
        "token_secret": "",
        "auth_token_expiry": expires_at,
    }

    return standard_response(
        message=SuccessMessages.PASSWORD_RESET_SUCCESS,
        request=request,
        data=response_data,
    )
