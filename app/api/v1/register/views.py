from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    IntentEnum,
    RegisterWithProfileRequest,
    ResendOTPRequest,
    VerifyOTPRegisterRequest,
)
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.register_otp import GenerateOtpService
from app.api.v1.service.register_service import UserVerifyService
from app.api.v1.service.register_task import get_device_info
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

    response_data = {LoginParams.REDIRECT_URL: redirect_url}
    return standard_response(
        message=SuccessMessages.USER_CREATED_REDIRECT_OTP,
        request=request,
        data=response_data,
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

    # 1. Verify and Consume OTP
    await _verify_and_consume_otp(cache, receiver, receiver_type, intent.value, otp)

    if intent == IntentEnum.FORGOT_PASSWORD:
        redirect_url = RedirectTemplates.SET_FORGOT_PASSWORD.format(
            type=receiver_type,
            receiver=receiver,
            intent=intent.value,
        )
        return standard_response(
            message=SuccessMessages.OTP_VERIFIED,
            request=request,
            data={LoginParams.REDIRECT_URL: redirect_url},
        )

    # 2. Retrieve Cached Registration Data
    cached_data = await _get_cached_registration_data(cache, receiver)

    # 3. Register User in DB
    user_rows = await _insert_user_record(db_session, cached_data, receiver_type)
    user_id = user_rows[0][ProcessParams.ID]

    # 4. Handle User Profile Creation
    await _create_user_profile(db_session, user_id, cached_data)

    # 5. Log OTP Verification
    await _log_otp_verification(db_session, user_id, cached_data)

    await db_session.commit()

    # 6. Clear cache
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA,
        identifier=receiver,
    )
    await cache.delete(cache_key)

    # 7. Device Registration and Auth Token
    auth_token, token_expiry = await _finalize_registration_and_auth(
        request,
        db_session,
        user_id,
        headers,
        cache,
    )

    # 8. Prepare response
    data_dict: dict[str, Any] = dict(user_rows[0])
    data_dict[RequestParams.TOKEN] = auth_token
    data_dict[RequestParams.TOKEN_EXPIRY] = token_expiry
    data_dict[ProcessParams.ID] = str(user_id)

    return standard_response(
        request=request,
        message=SuccessMessages.USER_REGISTERED_VERIFIED,
        data=data_dict,
    )


async def _verify_and_consume_otp(
    cache: Redis,
    receiver: str,
    receiver_type: str,
    intent: str,
    otp: str,
) -> None:
    """Verify and delete the OTP from cache."""
    template = (
        CacheKeyTemplates.OTP_EMAIL
        if receiver_type == RequestParams.EMAIL
        else CacheKeyTemplates.OTP_MOBILE
    )
    redis_key = template.format(receiver=receiver, intent=intent)
    cached_otp = await cache.get(redis_key)

    # 1. Check if OTP exists
    if not cached_otp:
        raise OtpExpiredError

    # 2. Verify OTP
    if (isinstance(cached_otp, bytes) and cached_otp.decode() != otp) or (
        isinstance(cached_otp, str) and cached_otp != otp
    ):
        from app.core.exceptions.exceptions import OtpInvalidError

        raise OtpInvalidError

    # 3. Consume OTP
    await cache.delete(redis_key)


async def _get_cached_registration_data(cache: Redis, receiver: str) -> dict[str, Any]:
    """Retrieve cached registration data."""
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA,
        identifier=receiver,
    )
    cached_data = await get_cache(cache, cache_key)
    if not cached_data:
        raise RegistrationSessionClosedError
    return cached_data


async def _insert_user_record(
    db_session: AsyncSession,
    cached_data: dict[str, Any],
    receiver_type: str,
) -> Any:
    """Insert user record into DB."""
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
    if not user_rows:
        raise ValidationError(message="Failed to create user.")
    return user_rows


async def _create_user_profile(
    db_session: AsyncSession,
    user_id: Any,
    cached_data: dict[str, Any],
) -> None:
    """Generate name and insert user profile."""
    # Name Generation Logic
    raw_name = cached_data.get(LoginParams.NAME)
    if not raw_name:
        email_val = cached_data.get(RequestParams.EMAIL)
        if email_val and isinstance(email_val, str):
            raw_name = email_val.split("@")[0]
        else:
            user_count_rows = await execute_query(
                query=UserQueries.GET_USER_COUNT,
                db_session=db_session,
                params={},
            )
            # user_count_rows returns list of RowMapping
            # Use string key if possible or handle indexing for Mypy
            count = user_count_rows[0][0] if user_count_rows else 0  # type: ignore
            raw_name = f"user{count}"

    # Split name into firstname and lastname
    firstname = raw_name
    lastname = None
    if raw_name and " " in raw_name.strip():
        parts = raw_name.strip().split(" ", 1)
        firstname = parts[0]
        lastname = parts[1]

    # Handle birth_date conversion
    birth_date = cached_data.get(LoginParams.BIRTH_DATE)
    if birth_date and isinstance(birth_date, str):
        try:
            from datetime import date

            birth_date = date.fromisoformat(birth_date)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse birth_date: {birth_date}")
            birth_date = None

    # Insert User Profile
    profile_params = {
        RequestParams.USER_ID: user_id,
        "firstname": firstname,
        "lastname": lastname,
        LoginParams.BIRTH_DATE: birth_date,
        LoginParams.AVATAR_ID: cached_data.get(LoginParams.AVATAR_ID),
        "image_url": cached_data.get(LoginParams.PROFILE_IMAGE),
    }
    await execute_query(
        query=UserQueries.INSERT_USER_PROFILE,
        db_session=db_session,
        params=profile_params,
    )


async def _log_otp_verification(
    db_session: AsyncSession,
    user_id: Any,
    cached_data: dict[str, Any],
) -> None:
    """Log successful OTP verification."""
    await execute_query(
        query=UserQueries.INSERT_OTP_VERIFICATION,
        db_session=db_session,
        params={
            RequestParams.USER_ID: user_id,
            RequestParams.EMAIL: cached_data.get(RequestParams.EMAIL),
            RequestParams.MOBILE: cached_data.get(RequestParams.MOBILE),
            RequestParams.CALLING_CODE: cached_data.get(RequestParams.CALLING_CODE),
        },
    )


async def _finalize_registration_and_auth(
    request: Request,
    db_session: AsyncSession,
    user_id: Any,
    headers: dict[str, Any],
    cache: Redis,
) -> tuple[str, int]:
    """Register device and generate auth token."""
    device_id = headers.get(RequestParams.DEVICE_ID)
    device_info = await get_device_info(request)

    if device_id:
        # Check if device exists
        device_attrs = await execute_query(
            query=UserQueries.CHECK_DEVICE_EXISTS,
            db_session=db_session,
            params={RequestParams.DEVICE_ID: device_id},
        )

        if not device_attrs:
            # Register device initially without token
            await execute_query(
                query=UserQueries.INSERT_DEVICE,
                db_session=db_session,
                params={
                    RequestParams.DEVICE_ID: device_id,
                    RequestParams.USER_ID: user_id,
                    RequestParams.DEVICE_NAME: device_info[RequestParams.DEVICE_NAME],
                    RequestParams.DEVICE_TYPE: device_info[RequestParams.DEVICE_TYPE],
                    RequestParams.PLATFORM: device_info[RequestParams.PLATFORM],
                    RequestParams.USER_TOKEN: None,
                },
            )

    # Generate Auth Token
    auth_token, token_expiry = await AuthService.generate_token(
        user=User(id=user_id),
        client_id=headers[RequestParams.API_CLIENT],
        cache=cache,
        device_id=device_id,
        db_session=db_session,
    )

    # Update Device with Token (Linking)
    if device_id:
        await execute_query(
            query=UserQueries.LINK_DEVICE_TO_USER,
            db_session=db_session,
            params={
                RequestParams.DEVICE_ID: device_id,
                RequestParams.USER_ID: user_id,
                RequestParams.USER_TOKEN: auth_token,
            },
        )

    await db_session.commit()
    return auth_token, token_expiry


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
