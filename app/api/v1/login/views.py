from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.api.queries import UserQueries
from app.api.v1.schemas import (
    LoginRequest, 
    UserProfileData, 
    ForgotPasswordRequest, 
    ForgotPasswordResponse,
    ChangePasswordRequest,
    ChangePasswordResponse
)
from app.api.v1.service.login_service import LoginService
from app.api.v1.service.forgot_password_service import ForgotPasswordService
from app.api.v1.service.change_password_service import ChangePasswordService
from app.api.v1.service.auth_service import AuthService
from app.cache.dependencies import get_redis_connection
from app.core.constants import SuccessMessages, Messages
from app.core.exceptions import InvalidInput
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform
from app.utils.standard_response import standard_response
from app.utils.validate_headers import validate_common_headers
from app.utils.validate_headers import validate_headers_without_auth
router = APIRouter()


@router.post("/login")
async def login_user(
    request: Request,
    login_data: LoginRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Authenticate user using Email or Mobile and Password.
    """
    device_id = headers.get("x-device-id") or headers.get("device_id")
    client_id = headers.get("x-api-client") or headers.get("api_client")

    # 1. Login via service
    user, token, expires_at = await LoginService.login_user(
        login_data=login_data,
        client_id=client_id,
        device_id=device_id,
        db_session=db_session,
        cache=cache
    )

    # 2. Fetch Full Profile for response
    profile_data_list = await execute_and_transform(
        UserQueries.GET_USER_PROFILE, 
        {"user_id": user["id"]}, 
        UserProfileData, 
        db_session
    )
    
    profile = profile_data_list[0] if profile_data_list else {
        "user_id": str(user["id"]),
        "email": user.get("email"),
        "name": user.get("name"),
    }

    # 3. Format response
    user_response = {
        "user_id": str(user["id"]),
        "email": profile.get("email"),
        "name": profile.get("name"),
        "image": profile.get("image")
    }

    response_data = {
        "auth_token": token,
        "auth_token_expiry": expires_at,
        "user": user_response
    }

    return standard_response(
        message=SuccessMessages.USER_LOGGED_IN,
        request=request,
        data=response_data,
    )


@router.post("/forgot_password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    headers: dict = Depends(validate_common_headers),
    db: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
):
    """
    Forgot password handler using email or mobile.
    Common headers are validated through validate_common_headers().
    """

    # Validate email or mobile
    if not payload.validate_email_or_mobile():
        raise InvalidInput(Messages.EMAIL_OR_MOBILE_REQUIRED)

    ip = request.client.host

    # Selecting email or mobile flow
    if payload.email:
        message = await ForgotPasswordService.forgot_password_email(
            db, payload.email, cache
        )
    else:
        message = await ForgotPasswordService.forgot_password_mobile(
            db,
            payload.mobile,
            payload.calling_code,
            ip,
            cache
        )

    return ForgotPasswordResponse(
        status=True,
        message=message,
        data={}
    )


@router.put("/change_password", response_model=ChangePasswordResponse)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    headers: dict = Depends(validate_common_headers),
    db_session: AsyncSession = Depends(get_db_session)
):

    print("HEADERS FROM DEPENDENCY:", headers)

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
        db_session=db_session
    )

    return ChangePasswordResponse(
        status=True,
        message=SuccessMessages.PASSWORD_CHANGED_SUCCESS,
        data={}
    )
