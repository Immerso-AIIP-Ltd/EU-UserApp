import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.schemas import (
    FriendInviteObject,
    FriendInviteRequest,
    ResendWaitlistOtpRequest,
    VerifyWaitlistRequest,
    WaitlistRequest,
)
from app.api.v1.service import register_deeplinks as deeplinks
from app.api.v1.service.register_commservice import call_communication_api
from app.api.v1.service.register_otp import GenerateOtpService
from app.api.v1.service.register_task import get_device_info
from app.cache.dependencies import get_redis_connection
from app.core.constants import (
    CacheKeyTemplates,
    CommParams,
    EmailTemplates,
    ErrorMessages,
    Intents,
    ProcessParams,
    RequestParams,
    ResponseParams,
    SuccessMessages,
)
from app.core.exceptions import exceptions
from app.core.exceptions.exceptions import OtpExpiredError
from app.db.dependencies import get_db_session
from app.db.utils import execute_query
from app.settings import settings
from app.utils.standard_response import standard_response
from app.utils.validate_headers import validate_headers_without_auth

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/waitlist")
async def join_waitlist(
    request: Request,
    payload: WaitlistRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    x_forwarded_for: str | None = Header(None, alias=RequestParams.X_FORWARDED_FOR),
) -> JSONResponse:
    """Join the waitlist using email or mobile and trigger OTP flow."""
    device_id = payload.device_id
    email_id = payload.email_id
    mobile = payload.mobile
    calling_code = payload.calling_code
    name = payload.name

    x_forwarded = x_forwarded_for or request.headers.get(RequestParams.X_FORWARDED_FOR)
    client_ip = (
        x_forwarded.split(",")[0].strip()
        if x_forwarded
        else (request.client.host if request.client else settings.redis_host)
    )

    if not device_id:
        raise exceptions.ValidationError(message=ErrorMessages.DEVICE_ID_REQUIRED)

    if not email_id and not (mobile and calling_code):
        raise exceptions.ValidationError(message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED)

    if email_id and not mobile:
        return await _process_email_flow(
            request,
            cache,
            db_session,
            device_id,
            email_id,
            name,
            client_ip,
        )

    if mobile and calling_code and not email_id:
        return await _process_mobile_flow(
            request,
            cache,
            db_session,
            device_id,
            mobile,
            calling_code,
            name,
            client_ip,
        )

    raise exceptions.ValidationError(message=ErrorMessages.PROVIDE_EMAIL_OR_MOBILE)


async def _process_email_flow(
    request: Request,
    cache: Redis,
    db_session: AsyncSession,
    device_id: str,
    email_id: str,
    name: str | None,
    x_forwarded_for: str,
) -> JSONResponse:
    # 1. Check existing device with email
    existing_device = await execute_query(
        query=UserQueries.GET_WAITLIST_BY_DEVICE_AND_EMAIL,
        params={RequestParams.DEVICE_ID: device_id, RequestParams.EMAIL: email_id},
        db_session=db_session,
    )

    if existing_device:
        entry = existing_device[0]
        if entry.is_verified:
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_QUEUE_STATUS.format(
                    entry.queue_number,
                    RequestParams.DEVICE_ID,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: entry.is_verified,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )

            # Resend OTP
            await GenerateOtpService.generate_otp(
                redis_client=cache,
                receiver=email_id,
                receiver_type=RequestParams.EMAIL,
                intent=Intents.WAITLIST,
                x_forwarded_for=x_forwarded_for,
                is_resend=True,
                db_session=db_session,
            )
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_OTP_RESENT.format(
                    RequestParams.DEVICE,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: False,
                    RequestParams.STATUS: ProcessParams.OTP_RESENT,
                },
            )

    # 2. Check if email exists
    existing_email = await execute_query(
        query=UserQueries.GET_WAITLIST_BY_EMAIL,
        params={RequestParams.EMAIL: email_id},
        db_session=db_session,
    )

    if existing_email:
        entry = existing_email[0]
        if entry.is_verified:
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_QUEUE_STATUS.format(
                    entry.queue_number,
                    RequestParams.EMAIL_ADDRESS,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: True,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )
            # Resend OTP
            await GenerateOtpService.generate_otp(
                redis_client=cache,
                receiver=email_id,
                receiver_type=RequestParams.EMAIL,
                intent=Intents.WAITLIST,
                x_forwarded_for=x_forwarded_for,
                is_resend=True,
                db_session=db_session,
            )
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_OTP_RESENT.format(RequestParams.EMAIL),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: False,
                    RequestParams.STATUS: ProcessParams.OTP_RESENT,
                },
            )

    # 3. New registration
    new_entry_rows = await execute_query(
        query=UserQueries.INSERT_WAITLIST_ENTRY,
        params={
            RequestParams.DEVICE_ID: device_id,
            RequestParams.EMAIL: email_id,
            RequestParams.MOBILE: "",
            RequestParams.CALLING_CODE: "",
        },
        db_session=db_session,
    )
    await db_session.commit()
    new_entry = new_entry_rows[0]

    await GenerateOtpService.generate_otp(
        redis_client=cache,
        receiver=email_id,
        receiver_type=RequestParams.EMAIL,
        intent=Intents.WAITLIST,
        x_forwarded_for=x_forwarded_for,
        db_session=db_session,
    )

    return standard_response(
        request=request,
        message=SuccessMessages.WAITLIST_OTP_SENT.format(RequestParams.EMAIL),
        data={
            RequestParams.QUEUE_NUMBER: str(new_entry.queue_number),
            RequestParams.IS_VERIFIED: False,
            RequestParams.STATUS: ProcessParams.OTP_SENT,
        },
    )


async def _process_mobile_flow(
    request: Request,
    cache: Redis,
    db_session: AsyncSession,
    device_id: str,
    mobile: str,
    calling_code: str,
    name: str | None,
    x_forwarded_for: str,
) -> JSONResponse:
    # 1. Check existing device
    existing_device = await execute_query(
        query=UserQueries.GET_WAITLIST_BY_DEVICE,
        params={RequestParams.DEVICE_ID: device_id},
        db_session=db_session,
    )

    if existing_device:
        entry = existing_device[0]
        if entry.is_verified:
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_QUEUE_STATUS.format(
                    entry.queue_number,
                    RequestParams.DEVICE_ID,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: entry.is_verified,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )
            await _send_mobile_otp(
                cache=cache,
                mobile=mobile,
                calling_code=calling_code,
                client_ip=x_forwarded_for,
                db_session=db_session,
                intent=Intents.WAITLIST,
                is_resend=True,
            )
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_OTP_RESENT.format(
                    RequestParams.DEVICE,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: False,
                    RequestParams.STATUS: ProcessParams.OTP_RESENT,
                },
            )

    # 2. Check existing mobile
    existing_mobile = await execute_query(
        query=UserQueries.GET_WAITLIST_BY_MOBILE,
        params={RequestParams.MOBILE: mobile, RequestParams.CALLING_CODE: calling_code},
        db_session=db_session,
    )

    if existing_mobile:
        entry = existing_mobile[0]
        if entry.is_verified:
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_QUEUE_STATUS.format(
                    entry.queue_number,
                    ProcessParams.MOBILE_NUMBER,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: True,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )
            await _send_mobile_otp(
                cache=cache,
                mobile=mobile,
                calling_code=calling_code,
                client_ip=x_forwarded_for,
                db_session=db_session,
                intent=Intents.WAITLIST,
                is_resend=True,
            )
            return standard_response(
                request=request,
                message=SuccessMessages.WAITLIST_OTP_RESENT.format(
                    ProcessParams.MOBILE_NUMBER,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: False,
                    RequestParams.STATUS: ProcessParams.OTP_RESENT,
                },
            )

    # 3. New registration
    new_entry_rows = await execute_query(
        query=UserQueries.INSERT_WAITLIST_ENTRY,
        params={
            RequestParams.DEVICE_ID: device_id,
            RequestParams.EMAIL: "",
            RequestParams.MOBILE: mobile,
            RequestParams.CALLING_CODE: calling_code,
        },
        db_session=db_session,
    )
    await db_session.commit()
    new_entry = new_entry_rows[0]

    await _send_mobile_otp(
        cache=cache,
        mobile=mobile,
        calling_code=calling_code,
        client_ip=x_forwarded_for,
        db_session=db_session,
        intent=Intents.WAITLIST,
    )

    return standard_response(
        request=request,
        message=SuccessMessages.WAITLIST_OTP_SENT.format(ProcessParams.MOBILE_NUMBER),
        data={
            RequestParams.QUEUE_NUMBER: str(new_entry.queue_number),
            RequestParams.IS_VERIFIED: False,
            RequestParams.STATUS: ProcessParams.OTP_SENT,
        },
    )


async def _send_mobile_otp(
    cache: Redis,
    mobile: str,
    calling_code: str,
    client_ip: str,
    db_session: AsyncSession,
    intent: str,
    is_resend: bool = False,
) -> None:
    await GenerateOtpService.generate_otp(
        redis_client=cache,
        receiver=f"{calling_code}{mobile}".lstrip("+"),
        receiver_type=RequestParams.MOBILE,
        intent=intent,
        x_forwarded_for=client_ip,
        db_session=db_session,
        mobile=mobile,
        calling_code=calling_code,
        is_resend=is_resend,
    )


async def _ensure_device_exists(
    db_session: AsyncSession,
    device_id: str,
    request: Request,
) -> None:
    # Check if device exists
    device_attrs = await execute_query(
        query=UserQueries.CHECK_DEVICE_EXISTS,
        db_session=db_session,
        params={RequestParams.DEVICE_ID: device_id},
    )
    if not device_attrs:
        # Create device
        device_info = await get_device_info(request)
        device_params = {
            RequestParams.DEVICE_ID: device_id,
            RequestParams.USER_ID: None,
            RequestParams.DEVICE_NAME: device_info.get(RequestParams.DEVICE_NAME),
            RequestParams.DEVICE_TYPE: device_info.get(RequestParams.DEVICE_TYPE),
            RequestParams.PLATFORM: device_info.get(RequestParams.PLATFORM),
            RequestParams.USER_TOKEN: None,
        }
        await execute_query(
            query=UserQueries.INSERT_DEVICE,
            db_session=db_session,
            params=device_params,
        )


@router.post("/waitlist_verify_otp")
async def verify_waitlist(
    request: Request,
    payload: VerifyWaitlistRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
) -> JSONResponse:
    """Verify OTP for waitlist entry."""
    email_id = payload.email_id
    mobile = payload.mobile
    calling_code = payload.calling_code
    otp = payload.otp

    if not email_id and not (mobile and calling_code):
        raise exceptions.ValidationError(message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED)

    # 1. Verify OTP
    if email_id:
        redis_key = CacheKeyTemplates.OTP_EMAIL.format(
            receiver=email_id,
            intent=Intents.WAITLIST,
        )
        cached_otp = await cache.get(redis_key)

        if (
            not cached_otp
            or (isinstance(cached_otp, bytes) and cached_otp.decode() != otp)
            or (isinstance(cached_otp, str) and cached_otp != otp)
        ):
            raise OtpExpiredError

        # Consume OTP
        await cache.delete(redis_key)

        # Get waitlist entry
        existing_entry = await execute_query(
            query=UserQueries.GET_WAITLIST_BY_EMAIL,
            params={RequestParams.EMAIL: email_id},
            db_session=db_session,
        )
    else:
        # Mobile verification
        receiver = f"{calling_code}{mobile}".lstrip("+")
        # Verify OTP
        redis_key = CacheKeyTemplates.OTP_MOBILE.format(
            receiver=receiver,
            intent=Intents.WAITLIST,
        )
        cached_otp = await cache.get(redis_key)

        if (
            not cached_otp
            or (isinstance(cached_otp, bytes) and cached_otp.decode() != payload.otp)
            or (isinstance(cached_otp, str) and cached_otp != payload.otp)
        ):
            raise exceptions.ValidationError(
                message=ErrorMessages.OTP_INVALID_OR_EXPIRED,
            )

        # Consume OTP
        await cache.delete(redis_key)

        # Get waitlist entry
        existing_entry = await execute_query(
            query=UserQueries.GET_WAITLIST_BY_MOBILE,
            params={
                RequestParams.MOBILE: mobile,
                RequestParams.CALLING_CODE: calling_code,
            },
            db_session=db_session,
        )

    if not existing_entry:
        raise exceptions.UserNotFoundError(
            message=ErrorMessages.WAITLIST_ENTRY_NOT_FOUND.format(ProcessParams.USER),
        )

    entry = existing_entry[0]

    # Update verification status
    updated_entry = await execute_query(
        query=UserQueries.UPDATE_WAITLIST_VERIFIED,
        params={ProcessParams.ID: entry.id},
        db_session=db_session,
    )

    await db_session.commit()

    updated_row = updated_entry[0]

    return standard_response(
        request=request,
        message=SuccessMessages.WAITLIST_QUEUE_STATUS.format(
            updated_row.queue_number,
            ResponseParams.VERIFICATION_SUCCESS,
        ),  # Or a simpler message
        data={
            RequestParams.QUEUE_NUMBER: str(updated_row.queue_number),
            RequestParams.IS_VERIFIED: True,
            RequestParams.STATUS: ResponseParams.VERIFIED,
        },
    )


@router.post("/waitlist_resend_otp")
async def resend_waitlist_otp(
    request: Request,
    payload: ResendWaitlistOtpRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    cache: Redis = Depends(get_redis_connection),
    x_forwarded_for: str | None = Header(None, alias=RequestParams.X_FORWARDED_FOR),
) -> JSONResponse:
    """Resend OTP for waitlist verification."""
    email_id = payload.email_id
    mobile = payload.mobile
    calling_code = payload.calling_code

    if not email_id and not (mobile and calling_code):
        raise exceptions.ValidationError(message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED)

    if email_id:
        # Check if waitlist entry exists
        existing_entry = await execute_query(
            query=UserQueries.GET_WAITLIST_BY_EMAIL,
            params={RequestParams.EMAIL: email_id},
            db_session=db_session,
        )
        if not existing_entry:
            raise exceptions.UserNotFoundError(
                message=ErrorMessages.WAITLIST_ENTRY_NOT_FOUND.format(
                    RequestParams.EMAIL,
                ),
            )

        if existing_entry[0].is_verified:
            return standard_response(
                request=request,
                message=SuccessMessages.EMAIL_ALREADY_VERIFIED,
                data={RequestParams.IS_VERIFIED: True},
            )

        # Generate and Send OTP
        await GenerateOtpService.generate_otp(
            redis_client=cache,
            receiver=email_id,
            receiver_type=RequestParams.EMAIL,
            intent=Intents.WAITLIST,
            db_session=db_session,
        )

    else:
        # Check if waitlist entry exists
        existing_entry = await execute_query(
            query=UserQueries.GET_WAITLIST_BY_MOBILE,
            params={
                RequestParams.MOBILE: mobile,
                RequestParams.CALLING_CODE: calling_code,
            },
            db_session=db_session,
        )
        if not existing_entry:
            raise exceptions.UserNotFoundError(
                message=ErrorMessages.WAITLIST_ENTRY_NOT_FOUND.format(
                    RequestParams.MOBILE_NUMBER,
                ),
            )

        if existing_entry[0].is_verified:
            return standard_response(
                request=request,
                message=SuccessMessages.MOBILE_ALREADY_VERIFIED,
                data={RequestParams.IS_VERIFIED: True},
            )

        # Generate and Send OTP
        receiver = f"{calling_code}{mobile}".lstrip("+")
        await GenerateOtpService.generate_otp(
            redis_client=cache,
            receiver=receiver,
            receiver_type=RequestParams.MOBILE,
            intent=Intents.WAITLIST,
            x_forwarded_for=x_forwarded_for,
            is_resend=True,
            db_session=db_session,
            mobile=mobile,
            calling_code=calling_code,
        )

    return standard_response(
        request=request,
        message=SuccessMessages.OTP_RESENT,
        data={RequestParams.SENT: True, RequestParams.IS_VERIFIED: False},
    )


@router.post("/friend_invite")
async def friend_invite(
    request: Request,
    payload: FriendInviteRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    x_device_id: str = Header(..., alias=RequestParams.X_DEVICE_ID),
) -> JSONResponse:
    """Invite a friend via email or mobile."""
    # 1. Resolve Inviter
    waitlist_entry, inviter_user_id = await _resolve_inviter(db_session, x_device_id)

    if not waitlist_entry:
        return standard_response(
            request=request,
            message=ErrorMessages.DEVICE_NOT_INVITED,
            data={
                RequestParams.INVITED: [],
                RequestParams.DUPLICATES: [],
                RequestParams.INVALID: [],
                RequestParams.FAILED: [],
            },
        )

    inviter_email = waitlist_entry.email
    waitlist_id = waitlist_entry.queue_number

    # 2. Check Inviter Registration
    if not inviter_user_id:
        logger.warning(
            f"{ErrorMessages.INVITER_NOT_FOUND}: Device {x_device_id}, "
            f"Email {inviter_email}",
        )
        return standard_response(
            request=request,
            message=SuccessMessages.INVITER_NOT_REGISTERED,
            data={
                RequestParams.INVITED: [],
                RequestParams.DUPLICATES: [],
                RequestParams.INVALID: [],
                RequestParams.FAILED: [
                    item.model_dump() if isinstance(item, FriendInviteObject) else item
                    for item in payload.invited_list
                ],
            },
        )

    # 3. Process Invites
    created_invites = []
    duplicate_invites = []
    invalid_items: list[Any] = []
    failed_items: list[Any] = []

    for item in payload.invited_list:
        invited_email, invited_mobile, invited_calling_code = _parse_invite_item(item)

        # Send Invite
        sent = await _send_invite_notification(
            invited_email,
            invited_mobile,
            invited_calling_code,
            inviter_email,
        )
        if not sent:
            failed_items.append(item)
            continue

        # Persist Invite
        status = await _persist_invite(
            db_session,
            inviter_user_id,
            waitlist_id,
            invited_email,
            invited_mobile,
            invited_calling_code,
        )

        if status == "created":
            created_invites.append(item)
        elif status == "duplicate":
            duplicate_invites.append(item)
        else:
            failed_items.append(item)

    return standard_response(
        request=request,
        message=SuccessMessages.FRIEND_INVITES_SENT.format(len(created_invites)),
        data={
            RequestParams.INVITED: [
                item.model_dump() if isinstance(item, FriendInviteObject) else item
                for item in created_invites
            ],
            RequestParams.DUPLICATES: [
                item.model_dump() if isinstance(item, FriendInviteObject) else item
                for item in duplicate_invites
            ],
            RequestParams.INVALID: [
                item.model_dump() if isinstance(item, FriendInviteObject) else item
                for item in invalid_items
            ],
            RequestParams.FAILED: [
                item.model_dump() if isinstance(item, FriendInviteObject) else item
                for item in failed_items
            ],
        },
    )


async def _resolve_inviter(
    db_session: AsyncSession,
    x_device_id: str,
) -> tuple[Any | None, int | None]:
    """Resolve waitlist entry and inviter user ID."""
    waitlist_entries = await execute_query(
        query=UserQueries.GET_WAITLIST_BY_DEVICE,
        params={RequestParams.DEVICE_ID: x_device_id},
        db_session=db_session,
    )
    if not waitlist_entries:
        return None, None

    waitlist_entry = waitlist_entries[0]
    inviter_user_id = waitlist_entry.id

    if not inviter_user_id:
        user_entry = await execute_query(
            query=UserQueries.GET_USER_BY_EMAIL,
            params={RequestParams.EMAIL: waitlist_entry.email},
            db_session=db_session,
        )
        if user_entry:
            inviter_user_id = user_entry[0].id

    return waitlist_entry, inviter_user_id


def _parse_invite_item(
    item: Any,
) -> tuple[str | None, str | None, str | None]:
    """Extract email, mobile, and calling code from invite item."""
    if isinstance(item, str):
        return item, None, None
    if isinstance(item, dict):
        return (
            item.get(RequestParams.EMAIL),
            item.get(RequestParams.MOBILE),
            item.get(RequestParams.CALLING_CODE),
        )
    # FriendInviteObject
    return item.email, item.mobile, item.calling_code


async def _send_invite_notification(
    invited_email: str | None,
    invited_mobile: str | None,
    invited_calling_code: str | None,
    inviter_email: str | None,
) -> bool:
    """Send invitation via Email or SMS."""
    try:
        if invited_email:
            email_payload = {
                CommParams.RECIPIENTS: [invited_email],
                CommParams.SUBJECT: EmailTemplates.FRIEND_INVITE_SUBJECT.format(
                    inviter_email,
                ),
                CommParams.MESSAGE: EmailTemplates.FRIEND_INVITE_MESSAGE.format(
                    inviter_email,
                    settings.web_url,
                ),
                CommParams.HTML_CONTENT: None,
                CommParams.TEMPLATE_ID: None,
            }
            resp = await call_communication_api(
                deeplinks.MAIL_SEND_URL,
                email_payload,
            )
            return bool(resp and resp.get(CommParams.STATUS) == ResponseParams.SUCCESS)

        if invited_mobile and invited_calling_code:
            sms_payload = {
                RequestParams.MOBILE: invited_mobile,
                RequestParams.CALLING_CODE: invited_calling_code,
                CommParams.MESSAGE: None,
                CommParams.VARIABLES: {CommParams.VAR: invited_mobile},
            }
            resp = await call_communication_api(deeplinks.SMS_SEND_URL, sms_payload)
            return bool(resp and resp.get(CommParams.STATUS) == ResponseParams.SUCCESS)

    except Exception as e:
        logger.error(f"{ErrorMessages.INVITE_SEND_FAILED}: {e}")
        return False

    return False


async def _persist_invite(
    db_session: AsyncSession,
    inviter_user_id: int | None,
    waitlist_id: int,
    invited_email: str | None,
    invited_mobile: str | None,
    invited_calling_code: str | None,
) -> str:
    """Insert invite into database. Returns 'created', 'duplicate', or 'failed'."""
    try:
        invited_user_id = None
        if invited_email:
            existing = await execute_query(
                UserQueries.GET_USER_BY_EMAIL,
                {RequestParams.EMAIL: invited_email},
                db_session,
            )
            if existing:
                invited_user_id = existing[0].id
        elif invited_mobile:
            existing = await execute_query(
                UserQueries.GET_USER_BY_MOBILE,
                {
                    RequestParams.MOBILE: invited_mobile,
                    RequestParams.CALLING_CODE: invited_calling_code,
                },
                db_session,
            )
            if existing:
                invited_user_id = existing[0].id

        res = await execute_query(
            query=UserQueries.INSERT_FRIEND_INVITE,
            params={
                RequestParams.INVITER_ID: inviter_user_id,
                RequestParams.INVITED_EMAIL: invited_email,
                RequestParams.INVITED_MOBILE: invited_mobile,
                RequestParams.INVITED_CALLING_CODE: invited_calling_code,
                RequestParams.INVITED_USER_ID: invited_user_id,
                RequestParams.WAITLIST_ID: waitlist_id,
            },
            db_session=db_session,
        )
        await db_session.commit()
        return "created" if res else "duplicate"

    except Exception as e:
        logger.error(f"{ErrorMessages.INVITE_DB_INSERT_FAILED}: {e}")
        return "failed"
