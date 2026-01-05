from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.service.auth_service import AuthService
from app.api.v1.service.logout_service import UserLogoutService
from app.cache.dependencies import get_redis_connection
from app.core.constants import SuccessMessages
from app.core.exceptions import UserTokenNotFound
from app.db.dependencies import get_db_session
from app.utils.standard_response import standard_response
from app.utils.validate_headers import validate_common_headers

router = APIRouter()


@router.post("/logout")
async def logout_user(
    request: Request,
    headers: dict[str, Any] = Depends(validate_common_headers),
    db_session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    print(headers)
    """
    Logs out the user by invalidating the device token.
    Requires a valid x-api-token in headers.
    """
    token = headers.get("x-api-token") or headers.get("api_token")
    device_id = headers.get("x-device-id") or headers.get("device_id")

    # 1. Verify token and get user_id
    user_id = await AuthService.verify_user_token(headers, db_session)

    if not all([user_id, token, device_id]):
        raise UserTokenNotFound()

    await UserLogoutService.logout(
        user_uuid=user_id,
        token=token or "",
        device_id=device_id or "",
        db_session=db_session,
        cache=cache,
    )

    return standard_response(
        message=SuccessMessages.USER_LOGGED_OUT_SUCCESS,
        request=request,
        data={},
    )


@router.post("/deactivate")
async def deactivate_user(
    request: Request,
    headers: dict[str, Any] = Depends(validate_common_headers),
    db_session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """
    Deactivates the user account and logs them out.
    Requires a valid x-api-token in headers.
    """
    token = headers.get("x-api-token") or headers.get("api_token")
    device_id = headers.get("x-device-id") or headers.get("device_id")

    # 1. Verify token and get user_id
    user_id = await AuthService.verify_user_token(headers, db_session)

    if not all([user_id, token, device_id]):
        raise UserTokenNotFound()

    await UserLogoutService.deactivate_account(
        user_uuid=user_id,
        token=token or "",
        device_id=device_id or "",
        db_session=db_session,
        cache=cache,
    )

    return standard_response(
        message=SuccessMessages.USER_DEACTIVATED_SUCCESS,
        request=request,
        data={},
    )
