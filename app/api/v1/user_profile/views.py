from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    UpdateEmailMobileData,
    UpdateEmailMobileRequest,
    UpdateProfileRequest,
    UserProfileData,
)
from app.api.v1.service.register_otp import GenerateOtpService
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    Intent,
    LoginParams,
    RedirectTemplates,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    ProfileFetchError,
    UserNotFoundError,
)
from app.core.middleware.auth import get_user_from_x_token
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform
from app.utils.standard_response import standard_response
from app.utils.validate_headers import validate_common_headers, validate_headers_without_auth

router = APIRouter()


@router.get("/profile")
async def get_user_profile(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    current_user: dict[str, Any] = Depends(get_user_from_x_token),
) -> JSONResponse:
    """Get authenticated user's profile using x-api-token."""
    user_id = current_user.get(RequestParams.UUID) or current_user.get(
        RequestParams.USER_ID,
    )
    if not user_id:
        raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND)

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_USER_PROFILE,
        **{
            RequestParams.USER_ID: user_id,
            RequestParams.PLATFORM: headers.get(RequestParams.PLATFORM),
            RequestParams.VERSION: headers.get(RequestParams.APP_VERSION),
            RequestParams.COUNTRY: headers.get(RequestParams.COUNTRY),
        },
    )
    cached_data = await get_cache(cache, cache_key)
    if cached_data:
        return standard_response(
            message=SuccessMessages.USER_PROFILE_RETRIEVED,
            request=request,
            data=cached_data,
        )
    query = UserQueries.GET_USER_PROFILE
    params = {RequestParams.USER_ID: user_id}

    try:
        data = await execute_and_transform(query, params, UserProfileData, db_session)

        if not data or len(data) == 0:
            raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND)

        user_profile = data[0]

        await set_cache(
            cache,
            cache_key,
            user_profile,
            ttl=CacheTTL.TTL_USER_PROFILE,
        )

        return standard_response(
            message=SuccessMessages.USER_PROFILE_RETRIEVED,
            request=request,
            data=user_profile,
        )

    except UserNotFoundError:
        raise
    except Exception as e:
        logger.exception(e)
        raise ProfileFetchError(
            detail=f"{ErrorMessages.PROFILE_FETCH_FAILED}: {e!s}",
        ) from e


@router.put("/profile")
async def update_user_profile(
    request: Request,
    profile_update: UpdateProfileRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    current_user: dict[str, Any] = Depends(get_user_from_x_token),
) -> JSONResponse:
    """Update authenticated user's profile."""
    user_id = current_user.get(RequestParams.UUID) or current_user.get(
        RequestParams.USER_ID,
    )
    if not user_id:
        raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND)

    # Invalidate cache
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

    query = UserQueries.UPDATE_USER_PROFILE
    params = {
        RequestParams.USER_ID: user_id,
        RequestParams.NAME: profile_update.name,
        RequestParams.GENDER: profile_update.gender,
        RequestParams.ABOUT_ME: profile_update.about_me,
        RequestParams.BIRTH_DATE: profile_update.birth_date,
        RequestParams.NICK_NAME: profile_update.nick_name,
        RequestParams.COUNTRY: profile_update.country,
        RequestParams.AVATAR_ID: profile_update.avatar_id,
        RequestParams.PROFILE_IMAGE: profile_update.profile_image,
    }

    try:
        data = await execute_and_transform(query, params, UserProfileData, db_session)

        if not data or len(data) == 0:
            raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND)

        user_profile = data[0]

        # Update cache with new data
        await set_cache(
            cache,
            cache_key,
            user_profile,
            ttl=CacheTTL.TTL_USER_PROFILE,
        )

        return standard_response(
            message=SuccessMessages.PROFILE_UPDATED,
            request=request,
            data=user_profile,
        )

    except UserNotFoundError:
        raise
    except Exception as e:
        logger.exception(e)
        raise ProfileFetchError(
            detail=f"{ErrorMessages.PROFILE_FETCH_FAILED}: {e!s}",
        ) from e


@router.post("/update_email_mobile")
async def update_email_mobile(
    request: Request,
    contact_update: UpdateEmailMobileRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    current_user: dict[str, Any] = Depends(get_user_from_x_token),
) -> JSONResponse:
    """Update authenticated user's email or mobile."""
    user_id = current_user.get(RequestParams.UUID) or current_user.get(
        RequestParams.USER_ID,
    )
    if not user_id:
        raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND)

    # Invalidate cache
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

    query = UserQueries.UPDATE_EMAIL_MOBILE
    params = {
        RequestParams.USER_ID: user_id,
        RequestParams.EMAIL: contact_update.email,
        RequestParams.MOBILE: contact_update.mobile,
        RequestParams.CALLING_CODE: contact_update.calling_code,
    }

    try:
        data = await execute_and_transform(
            query,
            params,
            UpdateEmailMobileData,
            db_session,
        )

        if not data or len(data) == 0:
            raise UserNotFoundError(message=ErrorMessages.USER_NOT_FOUND)

        # Determine receiver and type
        rx_type = RequestParams.EMAIL if contact_update.email else RequestParams.MOBILE
        receiver = (
            contact_update.email
            if contact_update.email
            else f"{contact_update.calling_code}{contact_update.mobile}".lstrip("+")
        )

        # Generate OTP
        # We pass x_forwarded_for as IP.
        # Since this is an authenticated request, we can get client IP from request.
        client_ip = request.client.host if request.client else RequestParams.LOCALHOST
        # Check for x-forwarded-for header
        x_ff = request.headers.get("x-forwarded-for")
        if x_ff:
            client_ip = x_ff.split(",")[0].strip()

        await GenerateOtpService.generate_otp(
            redis_client=cache,
            receiver=receiver,
            receiver_type=rx_type,
            intent=Intent.UPDATE_PROFILE,
            x_forwarded_for=client_ip,
            is_resend=False,
            db_session=db_session,
            mobile=contact_update.mobile,
            calling_code=contact_update.calling_code,
        )

        # Construct Redirect URL
        redirect_url = RedirectTemplates.VERIFY_OTP.format(
            type=rx_type,
            receiver=receiver,
            intent=Intent.UPDATE_PROFILE,
        )

        return standard_response(
            message=(
                SuccessMessages.EMAIL_UPDATED
                if contact_update.email
                else SuccessMessages.MOBILE_UPDATED
            ),
            request=request,
            data={LoginParams.REDIRECT_URL: redirect_url},
        )

    except UserNotFoundError:
        raise
    except Exception as e:
        logger.exception(e)
        raise ProfileFetchError(
            detail=f"{ErrorMessages.PROFILE_FETCH_FAILED}: {e!s}",
        ) from e
