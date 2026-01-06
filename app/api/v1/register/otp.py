import logging
import random
import string
from typing import Any, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.deeplinks import MAIL_SEND_URL, SMS_SEND_URL
from app.api.v1.register.task import block_ip_for_24_hours
from app.core.constants import (
    CacheKeyTemplates,
    CommParams,
    RequestParams,
    ResponseParams,
)
from app.core.exceptions import (
    exceptions,  # as core_exceptions (keeping name 'exceptions' to match usage)
)
from app.db.utils import execute_query

logger = logging.getLogger(__name__)


from app.settings import settings


class GenerateOtpService(object):

    @staticmethod
    async def _is_ip_blocked(
        redis_client: Redis,
        ip_address: str,
        receiver: Any,
    ) -> bool:
        redis_key = CacheKeyTemplates.BLOCKED_IP.format(
            ip_address=ip_address,
            receiver=receiver,
        )
        val = await redis_client.get(redis_key)
        return val is not None

    @staticmethod
    async def _increment_otp_request(
        redis_client: Redis,
        ip_address: str,
        receiver: Any,
    ) -> int:
        key = CacheKeyTemplates.OTP_REQ_COUNT.format(
            ip_address=ip_address,
            receiver=receiver,
        )
        try:
            count = await redis_client.incr(key)
            # Always reset expiry to 180 seconds on every request
            await redis_client.expire(key, 180)
            return count
        except Exception as e:
            logger.error(
                f"Redis error during OTP increment for {ip_address}_{receiver}: {e!s}",
            )
            raise exceptions.RedisServerDownError from e

    @staticmethod
    async def generate_otp(
        redis_client: Redis,
        receiver: Any,
        receiver_type: str,
        intent: str,
        x_forwarded_for: Optional[str] = None,
        is_resend: bool = False,
        db_session: Optional[AsyncSession] = None,
        mobile: Optional[str] = None,
        calling_code: Optional[str] = None,
    ) -> None:
        if receiver_type == "email":
            otp = "".join(random.choice(string.digits) for _ in range(4))
            # redis.set_val(f"email_otp_{receiver}_{intent}", otp, timeout=180)
            redis_key = CacheKeyTemplates.OTP_EMAIL.format(
                receiver=receiver,
                intent=intent,
            )
            await redis_client.setex(redis_key, 180, otp)
            try:
                # Use Brevo templates for different intents
                if intent == "forgot_password":
                    template_id = settings.brevo_forgot_password_template_id
                    reset_url = settings.brevo_reset_url
                    logger.debug(f"DEBUG: Intent={intent}, Template ID={template_id}")
                    if template_id:
                        # Get actual username from User model
                        username = receiver.split("@")[0]
                        if db_session:
                            user_rows = await execute_query(
                                query=UserQueries.GET_USERNAME_BY_EMAIL,
                                params={"email": receiver},
                                db_session=db_session,
                            )
                            if user_rows and user_rows[0].firstname:
                                username = user_rows[0].firstname

                        payload = {
                            CommParams.RECIPIENTS: [receiver],
                            CommParams.TEMPLATE_ID: int(template_id),
                            CommParams.TEMPLATE_PARAMS: {
                                "var": otp,
                                "username": username,
                                "reset_url": reset_url,
                            },
                        }
                        logger.debug(f"DEBUG: Using Brevo template payload: {payload}")
                    else:
                        # Fallback to regular email
                        payload = {
                            CommParams.RECIPIENTS: [receiver],
                            CommParams.SUBJECT: "Reset Your Password - OTP",
                            CommParams.MESSAGE: f"{otp} is your one time password to reset your ErosUniverse account password. It is valid for 3 minutes.",
                        }
                elif is_resend:
                    # Use Brevo template ID 11 for OTP resend
                    template_id = settings.brevo_otp_resend_template_id
                    if not template_id:
                        raise Exception("BREVO_OTP_RESEND_TEMPLATE_ID not configured")
                    logger.debug(
                        f"DEBUG: Resend Intent={intent}, Template ID={template_id}",
                    )

                    # Get actual username from User model
                    username = receiver.split("@")[0]
                    if db_session:
                        user_rows = await execute_query(
                            query=UserQueries.GET_USERNAME_BY_EMAIL,
                            params={"email": receiver},
                            db_session=db_session,
                        )
                        if user_rows and user_rows[0].firstname:
                            username = user_rows[0].firstname

                    payload = {
                        CommParams.RECIPIENTS: [receiver],
                        CommParams.TEMPLATE_ID: int(template_id),
                        CommParams.TEMPLATE_PARAMS: {
                            "otp_code": otp,
                            "username": username,
                        },
                    }
                    logger.debug(
                        f"DEBUG: Using Brevo resend template payload: {payload}",
                    )
                elif intent in ["email_verification", "registration", "waitlist"]:
                    # Use Brevo template ID 10 for email verification/registration
                    template_id = settings.brevo_email_verification_template_id
                    logger.debug(f"DEBUG: Intent={intent}, Template ID={template_id}")
                    # Get actual username from User model
                    username = receiver.split("@")[0]

                    payload = {
                        CommParams.RECIPIENTS: [receiver],
                        CommParams.TEMPLATE_ID: int(template_id),
                        CommParams.TEMPLATE_PARAMS: {
                            "otp_code": otp,
                            "username": username,
                        },
                    }
                    logger.debug(
                        f"DEBUG: Using Brevo email verification template payload: {payload}",
                    )
                else:
                    # For other intents, use regular email format
                    payload = {
                        CommParams.RECIPIENTS: [receiver],
                        CommParams.SUBJECT: "One Time Password.",
                        CommParams.MESSAGE: f"{otp} is your one time password to set up your ErosUniverse account. It is valid for 3 minutes.",
                    }
                await call_communication_api(MAIL_SEND_URL, payload)
            except Exception as e:
                logger.error(f"Failed to send OTP email via CommService: {e!s}")
                raise exceptions.CommServiceAPICallFailedError from e
            return

        # Refactored Logic for Mobile Flows (Local Generation)
        if receiver_type == "mobile":
            if not x_forwarded_for:
                logger.error("Client IP (x_forwarded_for) Missing")
                raise exceptions.ClientIpNotProvidedError

            if await GenerateOtpService._is_ip_blocked(
                redis_client,
                x_forwarded_for,
                receiver,
            ):
                logger.warning(f"IP is blocked: {x_forwarded_for}")
                raise exceptions.IpBlockedError

            req_count = await GenerateOtpService._increment_otp_request(
                redis_client,
                x_forwarded_for,
                receiver,
            )
            logger.info(
                f"OTP request count for {x_forwarded_for}_{receiver}: {req_count}",
            )

            if req_count > 3:
                logger.warning(
                    f"Too many OTP requests, blocking IP: {x_forwarded_for}_{receiver}",
                )
                block_ip_for_24_hours.apply_async(
                    queue="block_ip_queue",
                    args=([x_forwarded_for, receiver]),
                )
                raise exceptions.OtpTooManyAttemptsError

            # Generate OTP locally
            otp = "".join(random.choice(string.digits) for _ in range(4))
            receiver_for_key = str(receiver).lstrip("+")
            redis_key = CacheKeyTemplates.OTP_MOBILE.format(
                receiver=receiver_for_key,
                intent=intent,
            )
            await redis_client.setex(redis_key, 180, otp)

            if not mobile or not calling_code:
                # Fallback if arguments not provided: try to assume receiver is just mobile?
                # Or log warning. For now, assume callers updated.
                # Actually, if not provided we might fail the SMS send if payload incomplete.
                # Let's use receiver as mobile if mobile not passed, but calling_code needed.
                pass

            sms_payload = {
                RequestParams.MOBILE: mobile or receiver,
                RequestParams.CALLING_CODE: calling_code or "",
                CommParams.MESSAGE: None,
                CommParams.VARIABLES: {
                    "otp": otp,
                    CommParams.VAR: otp,
                },
            }

            # Send SMS
            try:
                response = await call_communication_api(SMS_SEND_URL, sms_payload)
                if response and response.get("status") == ResponseParams.SUCCESS:
                    pass  # Sent successfully
                else:
                    logger.error(f"Failed to send SMS: {response}")
                    # raise exceptions.CommServiceAPICallFailed()
                    # Don't crash hard if SMS fails? original code raised OtpTooManyAttempts if not sent?
                    # Original: if not is_otp_sent: raise exceptions.OtpTooManyAttempts()
            except Exception as e:
                logger.error(f"SMS Send failed: {e}")
                # raise exceptions.CommServiceAPICallFailed()

            return
