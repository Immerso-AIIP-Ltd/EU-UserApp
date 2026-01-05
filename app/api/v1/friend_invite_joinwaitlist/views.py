import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.register import deeplinks
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.otp import GenerateOtpService
from app.api.v1.register.task import get_device_info
from app.api.v1.schemas import (
    FriendInviteRequest,
    FriendInviteResponse,
    ResendWaitlistOtpRequest,
    VerifyWaitlistRequest,
    WaitlistRequest,
)
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
from app.core.exceptions.exceptions import OtpExpired
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
    device_id = payload.device_id
    email_id = payload.email_id
    mobile = payload.mobile
    calling_code = payload.calling_code
    name = payload.name

    x_forwarded = x_forwarded_for or request.headers.get(RequestParams.X_FORWARDED_FOR)
    client_ip = (
        x_forwarded.split(",")[0].strip()
        if x_forwarded
        else (request.client.host if request.client else settings.REDIS_HOST)
    )

    if not device_id:
        raise exceptions.ValidationError(message=ErrorMessages.DEVICE_ID_REQUIRED)

    # Ensure device exists to satisfy Foreign Key constraint
    # await _ensure_device_exists(db_session=db_session, device_id=device_id, request=request)

    if not email_id and not (mobile and calling_code):
        raise exceptions.ValidationError(message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED)

    if email_id and not mobile:
        return await _process_email_flow(
            request, cache, db_session, device_id, email_id, name, client_ip,
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
                    entry.queue_number, RequestParams.DEVICE_ID,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: entry.is_verified,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )
        else:
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
                    entry.queue_number, RequestParams.EMAIL_ADDRESS,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: True,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )
        else:
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
                    entry.queue_number, RequestParams.DEVICE_ID,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: entry.is_verified,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )
        else:
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
                    entry.queue_number, ProcessParams.MOBILE_NUMBER,
                ),
                data={
                    RequestParams.QUEUE_NUMBER: str(entry.queue_number),
                    RequestParams.IS_VERIFIED: True,
                    RequestParams.STATUS: SuccessMessages.WAITLIST_ALREADY_EXISTS,
                },
            )
        else:
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
    intent: Intents,
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
    email_id = payload.email_id
    mobile = payload.mobile
    calling_code = payload.calling_code
    otp = payload.otp

    if not email_id and not (mobile and calling_code):
        raise exceptions.ValidationError(message=ErrorMessages.EMAIL_OR_MOBILE_REQUIRED)

    # 1. Verify OTP
    if email_id:
        redis_key = CacheKeyTemplates.OTP_EMAIL.format(
            receiver=email_id, intent=Intents.WAITLIST,
        )
        cached_otp = await cache.get(redis_key)

        if (
            not cached_otp
            or (isinstance(cached_otp, bytes) and cached_otp.decode() != otp)
            or (isinstance(cached_otp, str) and cached_otp != otp)
        ):
            raise OtpExpired()

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
            receiver=receiver, intent=Intents.WAITLIST,
        )
        cached_otp = await cache.get(redis_key)

        if (
            not cached_otp
            or (isinstance(cached_otp, bytes) and cached_otp.decode() != payload.otp)
            or (isinstance(cached_otp, str) and cached_otp != payload.otp)
        ):
            raise ValidationError(ErrorMessages.OTP_INVALID_OR_EXPIRED)

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
        raise exceptions.UserNotFound(
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
            updated_row.queue_number, ResponseParams.VERIFICATION_SUCCESS,
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
            raise exceptions.UserNotFound(
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
            raise exceptions.UserNotFound(
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


@router.post("/friend_invite", response_model=FriendInviteResponse)
async def friend_invite(
    request: Request,
    payload: FriendInviteRequest,
    db_session: AsyncSession = Depends(get_db_session),
    headers: dict[str, Any] = Depends(validate_headers_without_auth),
    x_device_id: str = Header(..., alias=RequestParams.X_DEVICE_ID),
) -> JSONResponse:
    # 1. Get Waitlist Entry
    waitlist_entries = await execute_query(
        query=UserQueries.GET_WAITLIST_BY_DEVICE,
        params={RequestParams.DEVICE_ID: x_device_id},
        db_session=db_session,
    )

    if not waitlist_entries:
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

    waitlist_entry = waitlist_entries[0]
    inviter_email = waitlist_entry.email
    # inviter_mobile = waitlist_entry.mobile
    # inviter_calling_code = waitlist_entry.calling_code
    inviter_user_id = waitlist_entry.id
    waitlist_id = waitlist_entry.queue_number

    # 2. Resolve Inviter User ID if missing
    if not inviter_user_id:
        user_entry = await execute_query(
            query=UserQueries.GET_USER_BY_EMAIL,
            params={RequestParams.EMAIL: inviter_email},
            db_session=db_session,
        )
        if user_entry:
            inviter_user_id = user_entry[0].id

    created_invites = []
    duplicate_invites = []
    invalid_items = []
    failed_items = []

    if not inviter_user_id:
        logger.warning(
            f"{ErrorMessages.INVITER_NOT_FOUND}: Device {x_device_id}, Email {inviter_email}",
        )
        return standard_response(
            request=request,
            message=SuccessMessages.INVITER_NOT_REGISTERED,
            data={
                RequestParams.INVITED: [],
                RequestParams.DUPLICATES: [],
                RequestParams.INVALID: [],
                RequestParams.FAILED: [
                    (
                        item.model_dump()
                        if hasattr(item, ProcessParams.MODEL_DUMP)
                        else item
                    )
                    for item in payload.invited_list
                ],
            },
        )

    # 3. Process Invites
    for item in payload.invited_list:
        invited_email = None
        invited_mobile = None
        invited_calling_code = None

        # Determine Invite Type
        if isinstance(item, str):  # EmailStr
            invited_email = item
        elif isinstance(
            item, dict,
        ):  # Should not happen due to Pydantic, but purely for safety
            invited_email = item.get(RequestParams.EMAIL)
            invited_mobile = item.get(RequestParams.MOBILE)
            invited_calling_code = item.get(RequestParams.CALLING_CODE)
        else:  # FriendInviteObject
            invited_email = item.email
            invited_mobile = item.mobile
            invited_calling_code = item.calling_code

        # Send Invite
        success = False
        try:
            if invited_email:
                # Email Invite
                email_payload = {
                    CommParams.RECIPIENTS: [invited_email],
                    CommParams.SUBJECT: EmailTemplates.FRIEND_INVITE_SUBJECT.format(
                        inviter_email,
                    ),
                    CommParams.MESSAGE: EmailTemplates.FRIEND_INVITE_MESSAGE.format(
                        inviter_email, settings.web_url,
                    ),
                    CommParams.HTML_CONTENT: None,
                    CommParams.TEMPLATE_ID: None,
                }
                # TODO: Use proper template if available

                resp = await call_communication_api(
                    deeplinks.MAIL_SEND_URL, email_payload,
                )
                if (
                    resp and resp.get(CommParams.STATUS) == ResponseParams.SUCCESS
                ):  # Check your comm service response structure
                    success = True
            elif invited_mobile and invited_calling_code:
                # SMS Invite
                sms_payload = {
                    RequestParams.MOBILE: invited_mobile,
                    RequestParams.CALLING_CODE: invited_calling_code,
                    CommParams.MESSAGE: None,
                    CommParams.VARIABLES: {CommParams.VAR: invited_mobile},
                }
                # Note: User snippet used NotificationService.send_Friend_invite_sms
                # We try to map to generic SMS or a specific endpoint if exists.
                # Assuming SMS_SEND_URL works or we need a specific one.
                # User provided logic: NotificationService.send_Friend_invite_sms with variables.
                # Let's try generic SMS send.

                resp = await call_communication_api(deeplinks.SMS_SEND_URL, sms_payload)
                if resp and resp.get(CommParams.STATUS) == ResponseParams.SUCCESS:
                    success = True

        except Exception as e:
            logger.error(f"{ErrorMessages.INVITE_SEND_FAILED}: {e}")
            failed_items.append(item)
            continue

        if not success:
            failed_items.append(item)
            continue

        # Insert into DB
        try:
            # Check if already invited (Optional, but DB has CONFLICT DO NOTHING)
            # We just try insert

            # We need invited_user_id if they exist?
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

            if res:
                created_invites.append(item)
            else:
                duplicate_invites.append(item)

        except Exception as e:
            logger.error(f"{ErrorMessages.INVITE_DB_INSERT_FAILED}: {e}")
            failed_items.append(item)

    return standard_response(
        request=request,
        message=SuccessMessages.FRIEND_INVITES_SENT.format(len(created_invites)),
        data={
            RequestParams.INVITED: [
                item.model_dump() if hasattr(item, ProcessParams.MODEL_DUMP) else item
                for item in created_invites
            ],
            RequestParams.DUPLICATES: [
                item.model_dump() if hasattr(item, ProcessParams.MODEL_DUMP) else item
                for item in duplicate_invites
            ],
            RequestParams.INVALID: [
                item.model_dump() if hasattr(item, ProcessParams.MODEL_DUMP) else item
                for item in invalid_items
            ],
            RequestParams.FAILED: [
                item.model_dump() if hasattr(item, ProcessParams.MODEL_DUMP) else item
                for item in failed_items
            ],
        },
    )
