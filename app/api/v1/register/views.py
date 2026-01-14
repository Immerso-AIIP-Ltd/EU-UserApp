import asyncio
import logging
import time
from datetime import date
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    EncryptedRequest,
    IntentEnum,
    RegisterWithProfileRequest,
    ResendOTPRequest,
    VerifyOTPRegisterRequest,
)
from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.device_service import DeviceService
from app.api.v1.service.fusionauth_service import FusionAuthService
from app.api.v1.service.register_otp import GenerateOtpService
from app.api.v1.service.register_service import UserVerifyService
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    DeviceNames,
    ErrorMessages,
    HeaderKeys,
    Intents,
    LoginParams,
    ProcessParams,
    RedirectTemplates,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    DecryptionFailedError,
    DeviceNotRegisteredError,
    OtpExpiredError,
    OtpInvalidError,
    RegistrationSessionClosedError,
    StateNotFoundError,
    UserCreationFailedError,
    UserExistsError,
    UserNotFoundError,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.utils import execute_query
from app.settings import settings
from app.utils.security import SecurityService
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
    payload: EncryptedRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    x_forwarded_for: str | None = Header(None, alias=RequestParams.X_FORWARDED_FOR),
) -> JSONResponse:
    """Sign Up - Step 1 (Check Existence and Register) with Encryption."""

    # 0. Check if device is registered
    await _validate_device_registered(headers, db_session)

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        reg_payload = RegisterWithProfileRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    # Use the injected header or request header
    x_forwarded = x_forwarded_for or request.headers.get(RequestParams.X_FORWARDED_FOR)
    client_ip = (
        x_forwarded.split(",")[0].strip()
        if x_forwarded
        else (request.client.host if request.client else "127.0.0.1")
    )

    state = await _check_user_existence_and_get_state(
        reg_payload,
        db_session,
        cache,
        client_ip,
    )

    if not state:
        raise StateNotFoundError

    # Cache Registration Data for Verification step
    identifier = (
        reg_payload.email
        if reg_payload.email
        else f"{reg_payload.calling_code}{reg_payload.mobile}".lstrip("+")
    )
    hashed_password = hash_password(reg_payload.password)
    registration_data = reg_payload.model_dump(mode=RequestParams.JSON)
    registration_data[LoginParams.PASSWORD] = hashed_password

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA,
        identifier=identifier,
    )
    await set_cache(cache, cache_key, registration_data, ttl=CacheTTL.TTL_FAST)

    redirect_url = RedirectTemplates.VERIFY_OTP.format(
        type=RequestParams.EMAIL if reg_payload.email else RequestParams.MOBILE,
        receiver=reg_payload.email if reg_payload.email else reg_payload.mobile,
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
    payload: EncryptedRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Sign Up - Step 2 (Verify OTP & Create) with Encryption."""

    # 0. Check if device is registered
    await _validate_device_registered(headers, db_session)

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        verify_payload = VerifyOTPRegisterRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    email = verify_payload.email
    mobile = verify_payload.mobile
    calling_code = verify_payload.calling_code
    intent = verify_payload.intent
    otp = verify_payload.otp

    receiver = email if email else f"{calling_code}{mobile}".lstrip("+")
    receiver_type = RequestParams.EMAIL if email else RequestParams.MOBILE

    # 1. Verify and Consume OTP
    is_bypass = (
        request.headers.get(HeaderKeys.X_LOAD_TEST_BYPASS)
        == settings.load_test_bypass_secret
    )
    if not is_bypass:
        await _verify_and_consume_otp(cache, receiver, receiver_type, intent.value, otp)

    if intent in [IntentEnum.FORGOT_PASSWORD, IntentEnum.UPDATE_PROFILE]:
        return await _handle_otp_redirect_or_callback(
            request,
            db_session,
            cache,
            headers,
            receiver,
            receiver_type,
            intent,
            mobile,
            calling_code,
        )

    # Register and Finalize
    cached_data = await _get_cached_registration_data(cache, receiver)
    return await _finalize_user_registration(
        request,
        db_session,
        cache,
        headers,
        receiver_type,
        cached_data,
    )


async def _handle_otp_redirect_or_callback(
    request: Request,
    db_session: AsyncSession,
    cache: Redis,
    headers: dict[str, Any],
    receiver: str,
    receiver_type: str,
    intent: IntentEnum,
    mobile: str | None = None,
    calling_code: str | None = None,
) -> JSONResponse:
    """Handle redirects or callbacks after OTP verification."""
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

    if intent == IntentEnum.UPDATE_PROFILE:
        # Fetch user and update verified status
        user_rows = await _get_user_by_receiver(
            db_session,
            receiver,
            receiver_type,
            mobile,
            calling_code,
        )
        if not user_rows:
            raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND)

        user_id = user_rows[0].id
        await execute_query(
            query=UserQueries.UPDATE_USER_VERIFIED,
            params={RequestParams.USER_ID: user_id, "type": receiver_type},
            db_session=db_session,
        )
        await db_session.commit()

        # Invalidate Profile Cache
        await _invalidate_profile_cache(cache, user_id, headers)

        return standard_response(
            message=SuccessMessages.OTP_VERIFIED,
            request=request,
            data={LoginParams.REDIRECT_URL: None},
        )

    raise ValidationError(message="Invalid intent for redirect")


async def _get_user_by_receiver(
    db_session: AsyncSession,
    receiver: str,
    receiver_type: str,
    mobile: str | None = None,
    calling_code: str | None = None,
) -> Any:
    """Helper to fetch user based on receiver type."""
    if receiver_type == RequestParams.EMAIL:
        return await execute_query(
            query=UserQueries.GET_USER_BY_EMAIL,
            params={RequestParams.EMAIL: receiver},
            db_session=db_session,
        )
    return await execute_query(
        query=UserQueries.GET_USER_BY_MOBILE,
        params={
            RequestParams.MOBILE: mobile,
            RequestParams.CALLING_CODE: calling_code,
        },
        db_session=db_session,
    )


async def _invalidate_profile_cache(
    cache: Redis,
    user_id: Any,
    headers: dict[str, Any],
) -> None:
    """Helper to invalidate user profile cache."""
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_USER_PROFILE,
        **{
            RequestParams.USER_ID: user_id,
            RequestParams.PLATFORM: headers.get(RequestParams.PLATFORM),
            RequestParams.VERSION: headers.get(RequestParams.APP_VERSION),
            RequestParams.COUNTRY: headers.get(RequestParams.COUNTRY),
        },
    )
    await cache.delete(cache_key)


async def _finalize_user_registration(
    request: Request,
    db_session: AsyncSession,
    cache: Redis,
    headers: dict[str, Any],
    receiver_type: str,
    cached_data: dict[str, Any],
) -> JSONResponse:
    """Finalize user registration process."""
    # 3. Register User in DB
    user_rows = await _insert_user_record(db_session, cached_data, receiver_type)
    user_id = user_rows[0][ProcessParams.ID]

    # 4. Handle User Profile Creation
    await _create_user_profile(db_session, user_id, cached_data)

    # 5. Log OTP Verification
    await _log_otp_verification(db_session, user_id, cached_data)

    await db_session.commit()

    # 6. Finalize registration and auth (FusionAuth sync and token generation)
    auth_token, refresh_token, token_expiry = await _finalize_registration_and_auth(
        request,
        db_session,
        user_id,
        headers,
        cache,
        cached_data,
    )

    # 7. Clear cache
    email_val = cached_data.get(RequestParams.EMAIL)
    mobile_val = cached_data.get(RequestParams.MOBILE)
    cc_val = cached_data.get(RequestParams.CALLING_CODE)
    receiver = email_val or f"{cc_val}{mobile_val}".lstrip("+")
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA,
        identifier=receiver,
    )
    await cache.delete(cache_key)

    # 8. Prepare response
    data_dict: dict[str, Any] = dict(user_rows[0])
    data_dict[RequestParams.TOKEN] = auth_token
    data_dict[RequestParams.REFRESH_TOKEN] = refresh_token
    data_dict[ProcessParams.REG_ACCESS_TOKEN] = auth_token
    data_dict[ProcessParams.REG_REFRESH_TOKEN] = refresh_token
    data_dict[RequestParams.TOKEN_EXPIRY] = token_expiry
    data_dict[ProcessParams.ID] = str(user_id)

    return standard_response(
        request=request,
        message=SuccessMessages.USER_REGISTERED_VERIFIED,
        data=data_dict,
    )


async def _validate_device_registered(
    headers: dict[str, Any],
    db_session: AsyncSession,
) -> None:
    """Validate that the device is registered."""
    device_id = headers.get(RequestParams.DEVICE_ID)
    if not device_id or not await DeviceService.is_device_registered(
        device_id,
        db_session,
    ):
        raise DeviceNotRegisteredError(ErrorMessages.DEVICE_NOT_REGISTERED)


async def _check_user_existence_and_get_state(
    reg_payload: RegisterWithProfileRequest,
    db_session: AsyncSession,
    cache: Redis,
    client_ip: str,
) -> Any:
    """Check if user exists and return the current state."""
    email = reg_payload.email
    mobile = reg_payload.mobile
    calling_code = reg_payload.calling_code

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
        return await UserVerifyService.get_user_state_by_email(cache, email, db_session)

    if mobile and calling_code:
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
            raise UserExistsError(message=ErrorMessages.USER_ALREADY_REGISTERED)
        return await UserVerifyService.get_user_state_by_mobile(
            cache,
            mobile,
            calling_code,
            client_ip,
            db_session,
        )

    raise ValidationError(message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED)


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

    # DEBUG LOGGING
    logger = logging.getLogger(__name__)
    logger.info(
        f"Verifying OTP for {receiver}. Received: {otp}. Cached Raw: {cached_otp}",
    )

    if (
        not cached_otp
        or (isinstance(cached_otp, bytes) and cached_otp.decode() != otp)
        or (isinstance(cached_otp, str) and cached_otp != otp)
    ):
        raise OtpExpiredError

    # 2. Verify OTP
    if (isinstance(cached_otp, bytes) and cached_otp.decode() != otp) or (
        isinstance(cached_otp, str) and cached_otp != otp
    ):
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
        raise UserCreationFailedError
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
            birth_date = date.fromisoformat(birth_date)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse birth_date: {birth_date}")
            birth_date = None

    # Insert User Profile
    profile_params = {
        RequestParams.USER_ID: user_id,
        RequestParams.FIRSTNAME: firstname,
        RequestParams.LASTNAME: lastname,
        LoginParams.BIRTH_DATE: birth_date,
        LoginParams.AVATAR_ID: cached_data.get(LoginParams.AVATAR_ID),
        RequestParams.IMAGE_URL: cached_data.get(LoginParams.PROFILE_IMAGE),
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
    cached_data: dict[str, Any],
) -> tuple[str | None, str | None, int | None]:
    """Register device, sync to FusionAuth, and generate auth token."""
    device_id = headers.get(RequestParams.DEVICE_ID)

    # 1. Device Registration (if needed)
    await _validate_device_registered(headers, db_session)

    # 2. Sync to FusionAuth and Issue Token
    auth_token = None
    token_expiry = None
    refresh_token = None

    user_uuid_str = str(user_id)
    user_email = cached_data.get(RequestParams.EMAIL)

    try:
        # Sync User
        await asyncio.to_thread(
            FusionAuthService.create_fusion_user,
            user_uuid_str,
            user_email,
        )

        # Issue Token
        fa_token = await asyncio.to_thread(
            FusionAuthService.issue_token,
            user_uuid_str,
            None,
            {RequestParams.DEVICE_ID: device_id},
        )

        if fa_token:
            auth_token = fa_token
            token_expiry = int(time.time()) + CacheTTL.TOKEN_EXPIRY

    except Exception as e:
        logger.error(f"FusionAuth Error: {e}")

    # 3. Create Refresh Token
    if auth_token:
        refresh_token = await AuthService.create_refresh_session(
            db_session=db_session,
            user_id=str(user_id),
            device_id=device_id or DeviceNames.UNKNOWN_DEVICE,
        )

    # 4. Link Device to User (Update local DB with FA token)
    if device_id and auth_token:
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
    return auth_token, refresh_token, token_expiry


@router.post("/resend_otp")
async def resend_otp(
    request: Request,
    payload: EncryptedRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    x_forwarded_for: str | None = Header(None, alias=RequestParams.X_FORWARDED_FOR),
) -> JSONResponse:
    """Resend OTP (If Expired) with Encryption."""

    # 0. Check if device is registered
    await _validate_device_registered(headers, db_session)

    try:
        decrypted_payload = SecurityService.decrypt_payload(
            encrypted_key=payload.key,
            encrypted_data=payload.data,
        )
        resend_payload = ResendOTPRequest(**decrypted_payload)
    except Exception as e:
        raise DecryptionFailedError(detail=f"Decryption failed: {e!s}") from e

    email = resend_payload.email
    mobile = resend_payload.mobile
    calling_code = resend_payload.calling_code
    intent = resend_payload.intent

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
