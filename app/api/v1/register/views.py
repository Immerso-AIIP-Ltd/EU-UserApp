
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.register import deeplinks
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.service import UserVerifyService
from app.api.v1.schemas import (
    RegisterWithProfileRequest,
    VerifyOTPRegisterRequest,
)
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    CallingCodeRequired,
    EmailMobileRequired,
    OtpExpired,
    PasswordRequired,
    UserExits,
    ValidationError,
)
from app.db.dependencies import get_db_session
from app.db.utils import execute_query
from app.utils.standard_response import standard_response
from app.utils.validate_headers import CommonHeaders, validate_common_headers

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

router = APIRouter()


@router.post("/register_with_profile")
async def register_with_profile(
    request: Request,
    payload: RegisterWithProfileRequest,
    db_session: AsyncSession = Depends(get_db_session),
    x_forwarded_for: str | None = Header(None, alias="X-Forwarded-For"), #constant
    headers: CommonHeaders = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Sign Up - Step 1 (Check Existence and Register)"""
    """cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_DEVICE_INVITE_STATUS,
        payload=payload,
        platform=headers.platform,
        version=headers.app_version,
        country=headers.country,
    )

    cached_data = await get_cache(cache, cache_key)
    if cached_data:
        return standard_response(
            message=SuccessMessages.USER_CREATED_REDIRECT_OTP,
            request=request,
            data=cached_data,
        )"""

    email = payload.email
    mobile = payload.mobile
    calling_code = payload.calling_code

    # x_forwarded = headers.get("x-forwarded-for") # CommonHeaders has no get method
    # Use the injected header or request header
    x_forwarded = x_forwarded_for or request.headers.get("x-forwarded-for")
    client_ip = x_forwarded.split(",")[0].strip() if x_forwarded else request.client.host
    print("client", client_ip)
    if email:
        user_exists = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                "email": email,
                "mobile": None,
                "calling_code": None,
            },
            db_session=db_session,
        )
        if user_exists:
            raise UserExits()
        state = await UserVerifyService.get_user_state_by_email(cache, email, db_session)

    elif mobile and calling_code:
        user_exists = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                "email": None,
                "mobile": mobile,
                "calling_code": calling_code,
            },
            db_session=db_session,
        )
        if user_exists:
            raise UserExits(
                message=ErrorMessages.USER_ALREADY_REGISTERED,
            )
        state = await UserVerifyService.get_user_state_by_mobile(cache, mobile, calling_code, client_ip, db_session)

    else:
        raise ValidationError(
            message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED,
        )
    if not payload.email and not payload.mobile:
        raise EmailMobileRequired(
            message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED,
        )

    if payload.mobile and not payload.calling_code:
        raise CallingCodeRequired(
            message=ErrorMessages.CALLING_CODE_REQUIRED,
        )

    if not payload.password:
        raise PasswordRequired(
            message=ErrorMessages.PASSWORD_REQUIRED,
        )
    if not state:
        raise ValidationError(
            message=ErrorMessages.STATE_NOT_FOUND,
        )

    # Cache Registration Data for Verification step
    identifier = payload.email if payload.email else f"{payload.calling_code}{payload.mobile}"
    hashed_password = hash_password(payload.password)
    registration_data = payload.model_dump(mode="json")
    registration_data["password"] = hashed_password
    cache_key = build_cache_key(CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA, identifier=identifier)
    await set_cache(cache, cache_key, registration_data, ttl=CacheTTL.TTL_FAST)


    redirect_url = (
        f"erosnowapp://verify_otp?"
        f"email={payload.email}&intent=registration"
        if payload.email
        else f"erosnowapp://verify_otp?"
             f"mobile={payload.mobile}&intent=registration"
    )

    return standard_response(
        message=SuccessMessages.USER_CREATED_REDIRECT_OTP,
        request=request,
        data={"redirect_url": redirect_url},
    )


@router.post("/verify_otp_register")
async def verify_otp_register(
    request: Request,
    payload: VerifyOTPRegisterRequest,
    db_session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Sign Up - Step 2 (Verify OTP & Create)
    """
    email = payload.email
    mobile = payload.mobile
    calling_code = payload.calling_code
    intent = payload.intent
    otp = payload.otp

    receiver = email if email else f"{calling_code}{mobile}"
    receiver_type = ResponseParams.EMAIL if email else ResponseParams.MOBILE       # constant

    # 1. Verify OTP
    if receiver_type == ResponseParams.EMAIL:
        redis_key = f"email_otp_{email}_{intent.value}"
        cached_otp = await cache.get(redis_key)
        if not cached_otp or cached_otp != otp:
             raise OtpExpired(message = ErrorMessages.OtpExpired)
        # Consume OTP?
        await cache.delete(redis_key)
    else:
        # Verify Mobile OTP via external service
        verify_payload = {
            "receiver": receiver,
            "otp": otp,
            "intent": intent.value,
        }
        response = call_communication_api(deeplinks.VERIFY_OTP_URL, verify_payload)
        if response.get("status") != "success" or not response.get("data"):  # constant
             raise ValidationError(message=OTP_EXPIRED)

    # 2. Retrieve Cached Registration Data
    cache_key = build_cache_key(CacheKeyTemplates.CACHE_KEY_REGISTRATION_DATA, identifier=receiver)
    cached_data = await get_cache(cache, cache_key)
    if not cached_data:
       raise ValidationError(message="Registration session expired. Please try again.")  # constant

    # 3. Register User in DB
    # cached_data contains: email, mobile, calling_code, password (hashed), name, ...
    # Ensure all required params for query are present
    params = {
        "email": cached_data.get("email"),
        "mobile": cached_data.get("mobile"),
        "calling_code": cached_data.get("calling_code"),
        "password": cached_data.get("password"),
        "name": cached_data.get("name"),
        "avatar_id": cached_data.get("avatar_id"),
        "birth_date": cached_data.get("birth_date"),
        "profile_image": cached_data.get("profile_image"),
    }

    user_rows = await execute_query(
        query=UserQueries.REGISTER_WITH_PROFILE,
        params=params,
        db_session=db_session,
    )

    # Clear cache
    await cache.delete(cache_key)

    data = user_rows[0] if user_rows else {}
    return standard_response(message="User verified and registered successfully", data=data)


@router.post("/resend_otp")
async def resend_otp():
    """
    Resend OTP (If Expired)
    """
    return standard_response(message="OTP resent", data={"sent": True})
