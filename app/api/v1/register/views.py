from typing import Any
import logging

import bcrypt
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.register.otp import GenerateOtpService
from app.api.v1.register.service import UserVerifyService
from app.api.v1.register.task import get_device_info
from app.api.v1.schemas import (
    RegisterWithProfileRequest,
    ResendOTPRequest,
    VerifyOTPRegisterRequest,
)
from app.api.v1.service.auth_service import AuthService
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    Intents,
    LoginParams,
    ProcessParams,
    RedirectTemplates,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    CallingCodeRequiredError,
    EmailMobileRequiredError,
    OtpExpiredError,
    PasswordRequiredError,
    RegistrationSessionClosedError,
    UserExistsError,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.models.user_app import User
from app.db.utils import execute_query
from app.utils.standard_response import standard_response
from app.utils.validate_headers import (
    validate_headers_without_auth,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes: bytes
    if isinstance(password, str):
        password_bytes = password.encode(LoginParams.UTF8)
    else:
        password_bytes = password

    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode(LoginParams.UTF8)


def get_hashed_password(password: str) -> str:
    """Hash a password using bcrypt (alias for hash_password)."""
    password_bytes: bytes
    if isinstance(password, str):
        password_bytes = password.encode(LoginParams.UTF8)
    else:
        password_bytes = password
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode(LoginParams.UTF8)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    plain_bytes: bytes = (
        plain_password.encode(LoginParams.UTF8)
        if isinstance(plain_password, str)
        else plain_password
    )
    hashed_bytes: bytes = (
        hashed_password.encode(LoginParams.UTF8)
        if isinstance(hashed_password, str)
        else hashed_password
    )

    return bcrypt.checkpw(plain_bytes, hashed_bytes)


router = APIRouter()


@router.post("/register_with_profile")
async def register_with_profile(
    request: Request,
    payload: RegisterWithProfileRequest,
    db_session: AsyncSession = Depends(get_db_session),
    x_forwarded_for: str | None = Header(None, alias=RequestParams.X_FORWARDED_FOR),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Sign Up - Step 1 (Check Existence and Register)."""
    email = payload.email
    mobile = payload.mobile
    calling_code = payload.calling_code

    # Use the injected header or request header
    x_forwarded = x_forwarded_for or request.headers.get(RequestParams.X_FORWARDED_FOR)
    client_ip = (
        x_forwarded.split(",")[0].strip()
        if x_forwarded
        else (request.client.host if request.client else "127.0.0.1")
    )

    if email:
        user_exists = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                RequestParams.EMAIL: email,
                RequestParams.MOBILE: None,
                RequestParams.CALLING_CODE: None,
            },
            db_session=db_session,
        )
        if user_exists:
            raise UserExistsError
        state = await UserVerifyService.get_user_state_by_email(
            cache,
            email,
            db_session,
        )

    elif mobile and calling_code:
        user_exists = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                RequestParams.EMAIL: None,
                RequestParams.MOBILE: mobile,
                RequestParams.CALLING_CODE: calling_code,
            },
            db_session=db_session,
        )
        if user_exists:
            raise UserExistsError(
                message=ErrorMessages.USER_ALREADY_REGISTERED,
            )
        state = await UserVerifyService.get_user_state_by_mobile(
            cache,
            mobile,
            calling_code,
            client_ip,
            db_session,
        )

    else:
        raise ValidationError(
            message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED,
        )
    if not payload.email and not payload.mobile:
        raise EmailMobileRequiredError(
            message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED,
        )

    if payload.mobile and not payload.calling_code:
        raise CallingCodeRequiredError(
            message=ErrorMessages.CALLING_CODE_REQUIRED,
        )

    if not payload.password:
        raise PasswordRequiredError(
            message=ErrorMessages.PASSWORD_REQUIRED,
        )
    if not state:
        raise ValidationError(
            message=ErrorMessages.STATE_NOT_FOUND,
        )

    # Cache Registration Data for Verification step
    identifier = (
        payload.email
        if payload.email
        else f"{payload.calling_code}{payload.mobile}".lstrip("+")
    )
    hashed_password = hash_password(payload.password)
    registration_data = payload.model_dump(mode=RequestParams.JSON)
    registration_data[LoginParams.PASSWORD] = hashed_password
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA,
        identifier=identifier,
    )
    await set_cache(cache, cache_key, registration_data, ttl=CacheTTL.TTL_FAST)

    redirect_url = RedirectTemplates.VERIFY_OTP.format(
        type=RequestParams.EMAIL if payload.email else RequestParams.MOBILE,
        receiver=payload.email if payload.email else payload.mobile,
        intent=Intents.REGISTRATION,
    )

    return standard_response(
        message=SuccessMessages.USER_CREATED_REDIRECT_OTP,
        request=request,
        data={LoginParams.REDIRECT_URL: redirect_url},
    )


@router.post("/verify_otp_register")
async def verify_otp_register(
    request: Request,
    payload: VerifyOTPRegisterRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Sign Up - Step 2 (Verify OTP & Create)."""
    email = payload.email
    mobile = payload.mobile
    calling_code = payload.calling_code
    intent = payload.intent
    otp = payload.otp

    receiver = email if email else f"{calling_code}{mobile}".lstrip("+")
    receiver_type = RequestParams.EMAIL if email else RequestParams.MOBILE

    # 1. Verify OTP
    template = (
        CacheKeyTemplates.OTP_EMAIL
        if receiver_type == RequestParams.EMAIL
        else CacheKeyTemplates.OTP_MOBILE
    )
    redis_key = template.format(receiver=receiver, intent=intent.value)
    cached_otp = await cache.get(redis_key)
    
    # DEBUG LOGGING
    logger = logging.getLogger(__name__)
    logger.info(f"Verifying OTP for {receiver}. Received: {otp}. Cached Raw: {cached_otp}")

    if (
        not cached_otp
        or (isinstance(cached_otp, bytes) and cached_otp.decode() != otp)
        or (isinstance(cached_otp, str) and cached_otp != otp)
    ):
        logger.warning(f"OTP Mismatch or Expired for {receiver}")
        raise OtpExpiredError

    await cache.delete(redis_key)

    # 2. Retrieve Cached Registration Data
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA,
        identifier=receiver,
    )
    cached_data = await get_cache(cache, cache_key)
    if not cached_data:
        raise RegistrationSessionClosedError

    # 3. Register User in DB
    # cached_data contains: email, mobile, calling_code, password (hashed), name, ...
    # Ensure all required params for query are present
    params = {
        RequestParams.EMAIL: cached_data.get(RequestParams.EMAIL),
        RequestParams.MOBILE: cached_data.get(RequestParams.MOBILE),
        RequestParams.CALLING_CODE: cached_data.get(RequestParams.CALLING_CODE),
        LoginParams.PASSWORD: cached_data.get(LoginParams.PASSWORD),
        LoginParams.NAME: cached_data.get(LoginParams.NAME),
        LoginParams.AVATAR_ID: cached_data.get(LoginParams.AVATAR_ID),
        LoginParams.BIRTH_DATE: cached_data.get(LoginParams.BIRTH_DATE),
        LoginParams.PROFILE_IMAGE: cached_data.get(LoginParams.PROFILE_IMAGE),
        LoginParams.LOGIN_TYPE: receiver_type,
        LoginParams.TYPE: LoginParams.REGULAR,
    }
    user_rows = await execute_query(
        query=UserQueries.INSERT_USER,
        db_session=db_session,
        params=params,
    )
    await db_session.commit()

    # Clear cache
    await cache.delete(cache_key)
    data = dict(user_rows[0]) if user_rows else {}

    device_id = headers[RequestParams.DEVICE_ID]

    auth_token, token_expiry = await AuthService.generate_token(
        user=User(id=data[ProcessParams.ID]),
        client_id=headers[RequestParams.API_CLIENT],
        cache=cache,
        device_id=device_id,
        db_session=db_session,
    )
    
    # Sync with FusionAuth and Issue Token
    try:
        from app.api.v1.service.fusionauth_service import FusionAuthService
        import asyncio
        import time
        
        user_uuid_str = str(data[ProcessParams.ID])
        user_email = data.get(RequestParams.EMAIL)
        
        # 1. Sync User (Wait for it, because we need it to exist before issuing token)
        await asyncio.to_thread(FusionAuthService.create_fusion_user, user_uuid_str, user_email)
        
        # 2. Issue Token
        fa_token = await asyncio.to_thread(FusionAuthService.issue_token, user_uuid_str)
        
        if fa_token:
            auth_token = fa_token
            # Set expiry to match FA token (300s default in service -> 600s)
            token_expiry = int(time.time()) + 600
            
    except Exception as e:
        print(f"Failed to sync/issue FusionAuth token in register: {e}")
        # Log and continue using local token if FusionAuth fails
        pass

    await db_session.commit()
    # Device Registration
    device_info = await get_device_info(request)
    device_params = {
        RequestParams.DEVICE_ID: device_id,
        RequestParams.USER_ID: data[ProcessParams.ID],
        RequestParams.DEVICE_NAME: device_info[RequestParams.DEVICE_NAME],
        RequestParams.DEVICE_TYPE: device_info[RequestParams.DEVICE_TYPE],
        RequestParams.PLATFORM: device_info[RequestParams.PLATFORM],
        RequestParams.USER_TOKEN: auth_token,
    }
    if device_id:
        # if device id is not registered than we will register it
        device_attrs = await execute_query(
            query=UserQueries.CHECK_DEVICE_EXISTS,
            db_session=db_session,
            params={RequestParams.DEVICE_ID: device_id},
        )

        if not device_attrs:
            await execute_query(
                query=UserQueries.INSERT_DEVICE,
                db_session=db_session,
                params=device_params,
            )
            await db_session.commit()

    data_dict: dict[str, Any] = dict(data)  # type: ignore
    # attach token to response
    data_dict[RequestParams.TOKEN] = auth_token
    data_dict[RequestParams.TOKEN_EXPIRY] = token_expiry
    user_id = str(user_rows[0][ProcessParams.ID])
    data_dict[ProcessParams.ID] = user_id

    return standard_response(
        request=request,
        message=SuccessMessages.USER_REGISTERED_VERIFIED,
        data=data_dict,
    )


@router.post("/resend_otp")
async def resend_otp(
    request: Request,
    payload: ResendOTPRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    x_forwarded_for: str | None = Header(None, alias=RequestParams.X_FORWARDED_FOR),
) -> JSONResponse:
    """Resend OTP (If Expired)."""
    email = payload.email
    mobile = payload.mobile
    calling_code = payload.calling_code
    intent = payload.intent

    receiver = email if email else f"{calling_code}{mobile}".lstrip("+")
    receiver_type = RequestParams.EMAIL if email else RequestParams.MOBILE

    # Check if registration session exists
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA,
        identifier=receiver,
    )
    cached_data = await get_cache(cache, cache_key)
    if not cached_data:
        raise RegistrationSessionClosedError

    x_forwarded = x_forwarded_for or request.headers.get(RequestParams.X_FORWARDED_FOR)
    client_ip = (
        x_forwarded.split(",")[0].strip()
        if x_forwarded
        else (request.client.host if request.client else RequestParams.LOCALHOST)
    )

    await GenerateOtpService.generate_otp(
        redis_client=cache,
        receiver=receiver,
        receiver_type=receiver_type,
        intent=intent.value,
        x_forwarded_for=client_ip,
        is_resend=True,
        db_session=db_session,
        mobile=mobile,
        calling_code=calling_code,
    )

    return standard_response(
        request=request,
        message=SuccessMessages.OTP_RESENT,
        data={RequestParams.SENT: True},
    )
