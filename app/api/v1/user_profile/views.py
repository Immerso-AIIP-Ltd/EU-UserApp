
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
from app.cache.base import build_cache_key, get_cache, set_cache
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    ErrorMessages,
    RequestParams,
    SuccessMessages,
)
from app.core.exceptions.exceptions import (
    ProfileFetchException,
    UserNotFoundException,
)
from app.core.middleware.auth import get_current_user
from app.db.dependencies import get_db_session
from app.db.utils import execute_and_transform
from app.utils.standard_response import standard_response
from app.utils.validate_headers import validate_common_headers

router = APIRouter()


@router.get("/profile")
async def get_user_profile(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """
    Get authenticated user's profile using x-api-token.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise UserNotFoundException(detail=ErrorMessages.USER_NOT_FOUND)

    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_USER_PROFILE,
        **{
            RequestParams.USER_ID: user_id,
            "platform": headers.get("platform"),
            "version": headers.get("app_version"),
            "country": headers.get("country"),
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
            raise UserNotFoundException(detail=ErrorMessages.USER_NOT_FOUND)

        user_profile = data[0]

        await set_cache(cache, cache_key, user_profile, ttl=CacheTTL.TTL_USER_PROFILE)

        return standard_response(
            message=SuccessMessages.USER_PROFILE_RETRIEVED,
            request=request,
            data=user_profile,
        )

    except UserNotFoundException:
        raise
    except Exception as e:
        logger.exception(e)
        raise ProfileFetchException(
            detail=f"{ErrorMessages.PROFILE_FETCH_FAILED}: {e!s}",
        )


@router.put("/profile")
async def update_user_profile(
    request: Request,
    profile_update: UpdateProfileRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """
    Update authenticated user's profile.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise UserNotFoundException(detail=ErrorMessages.USER_NOT_FOUND)

    # Invalidate cache
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_USER_PROFILE,
        **{
            RequestParams.USER_ID: user_id,
            "platform": headers.get("platform"),
            "version": headers.get("app_version"),
            "country": headers.get("country"),
        },
    )
    await cache.delete(cache_key)

    query = UserQueries.UPDATE_USER_PROFILE
    params = {
        RequestParams.USER_ID: user_id,
        "name": profile_update.name,
        "gender": profile_update.gender,
        "about_me": profile_update.about_me,
        "birth_date": profile_update.birth_date,
        "nick_name": profile_update.nick_name,
        "country": profile_update.country,
        "avatar_id": profile_update.avatar_id,
        "profile_image": profile_update.profile_image,
    }

    try:
        data = await execute_and_transform(query, params, UserProfileData, db_session)

        if not data or len(data) == 0:
            raise UserNotFoundException(detail=ErrorMessages.USER_NOT_FOUND)

        user_profile = data[0]

        # Update cache with new data
        await set_cache(cache, cache_key, user_profile, ttl=CacheTTL.TTL_USER_PROFILE)

        return standard_response(
            message="Profile Updated",
            request=request,
            data=user_profile,
        )

    except UserNotFoundException:
        raise
    except Exception as e:
        logger.exception(e)
        raise ProfileFetchException(
            detail=f"{ErrorMessages.PROFILE_FETCH_FAILED}: {e!s}",
        )


@router.post("/update_email_mobile")
async def update_email_mobile(
    request: Request,
    contact_update: UpdateEmailMobileRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict = Depends(validate_common_headers),
    cache: Redis = Depends(get_redis_connection),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """
    Update authenticated user's email or mobile.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise UserNotFoundException(detail=ErrorMessages.USER_NOT_FOUND)

    # Invalidate cache
    cache_key = build_cache_key(
        CacheKeyTemplates.CACHE_KEY_USER_PROFILE,
        **{
            RequestParams.USER_ID: user_id,
            "platform": headers.get("platform"),
            "version": headers.get("app_version"),
            "country": headers.get("country"),
        },
    )
    await cache.delete(cache_key)

    query = UserQueries.UPDATE_EMAIL_MOBILE
    params = {
        RequestParams.USER_ID: user_id,
        "email": contact_update.email,
        "mobile": contact_update.mobile,
        "calling_code": contact_update.calling_code,
    }

    try:
        data = await execute_and_transform(
            query, params, UpdateEmailMobileData, db_session,
        )

        if not data or len(data) == 0:
            raise UserNotFoundException(detail=ErrorMessages.USER_NOT_FOUND)

        updated_contact = data[0]

        message = (
            "User Email updated successfully."
            if contact_update.email
            else "User Mobile updated successfully."
        )

        return standard_response(
            message=message,
            request=request,
            data=updated_contact,
        )

    except UserNotFoundException:
        raise
    except Exception as e:
        logger.exception(e)
        raise ProfileFetchException(
            detail=f"{ErrorMessages.PROFILE_FETCH_FAILED}: {e!s}",
        )
