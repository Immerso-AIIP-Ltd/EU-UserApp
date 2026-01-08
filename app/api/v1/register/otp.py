import logging
import secrets
import string
from typing import Any, Dict, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.register import deeplinks
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.task import block_ip_for_24_hours
from app.core.constants import (
    CacheKeyTemplates,
    CacheTTL,
    CeleryQueues,
    CommParams,
    EmailMessages,
    EmailSubjects,
    Intents,
    LogMessages,
    RequestParams,
    ResponseParams,
    TemplateParams,
)
from app.core.exceptions import (
    exceptions,
)
from app.db.utils import execute_query
from app.settings import settings

logger = logging.getLogger(__name__)


class GenerateOtpService:
    """Service to handle OTP generation and delivery via email or SMS."""

    @staticmethod
    async def _is_ip_blocked(
        redis_client: Redis,
        ip_address: str,
        receiver: Any,
    ) -> bool:
        """Check if an IP address is currently blocked for a receiver."""
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
        """Increment OTP request count for an IP-receiver pair."""
        key = CacheKeyTemplates.OTP_REQ_COUNT.format(
            ip_address=ip_address,
            receiver=receiver,
        )
        try:
            count = await redis_client.incr(key)
            # Always reset expiry to 180 seconds on every request
            await redis_client.expire(key, CacheTTL.OTP_EXPIRY)
            return count
        except Exception as e:
            logger.error(
                LogMessages.REDIS_ERROR_INCREMENT.format(ip_address, receiver, e),
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
        """Generate and send OTP based on receiver type (email or mobile)."""
        # Generate OTP locally using secrets for security (S311)
        otp = "".join(secrets.choice(string.digits) for _ in range(4))
        
        logger.info(f"Generating OTP for {receiver} (type={receiver_type}, intent={intent})")
        # DEBUG LOGGING FOR OTP
        logger.info(f"Generated OTP: {otp}")

        if receiver_type == RequestParams.EMAIL:
            await GenerateOtpService._handle_email_otp(
                redis_client,
                receiver,
                otp,
                intent,
                is_resend,
                db_session,
            )
        elif receiver_type == RequestParams.MOBILE:
            await GenerateOtpService._handle_mobile_otp(
                redis_client,
                receiver,
                otp,
                intent,
                x_forwarded_for,
                mobile,
                calling_code,
            )

    @staticmethod
    async def _handle_email_otp(
        redis_client: Redis,
        receiver: str,
        otp: str,
        intent: str,
        is_resend: bool,
        db_session: Optional[AsyncSession],
    ) -> None:
        """Handle logic for email-based OTP delivery."""
        redis_key = CacheKeyTemplates.OTP_EMAIL.format(
            receiver=receiver,
            intent=intent,
        )
        await redis_client.setex(redis_key, CacheTTL.OTP_EXPIRY, otp)

        try:
            payload: Dict[str, Any] = {}
            if intent == Intents.FORGOT_PASSWORD:
                payload = await GenerateOtpService._get_forgot_password_payload(
                    receiver,
                    otp,
                    db_session,
                )
            elif is_resend:
                payload = await GenerateOtpService._get_resend_payload(
                    receiver,
                    otp,
                    intent,
                    db_session,
                )
            elif intent in [Intents.REGISTRATION, Intents.WAITLIST]:
                payload = await GenerateOtpService._get_registration_payload(
                    receiver,
                    otp,
                    intent,
                    db_session,
                )
            else:
                payload = {
                    CommParams.RECIPIENTS: [receiver],
                    CommParams.SUBJECT: EmailSubjects.ONE_TIME_PASSWORD,
                    CommParams.MESSAGE: EmailMessages.ONE_TIME_PASSWORD.format(otp),
                }
            await call_communication_api(deeplinks.MAIL_SEND_URL, payload)
        except Exception as e:
            logger.error(LogMessages.EMAIL_SEND_FAILED.format(e))
            raise exceptions.CommServiceAPICallFailedError from e

    @staticmethod
    async def _handle_mobile_otp(
        redis_client: Redis,
        receiver: Any,
        otp: str,
        intent: str,
        x_forwarded_for: Optional[str],
        mobile: Optional[str],
        calling_code: Optional[str],
    ) -> None:
        """Handle logic for mobile-based OTP delivery (SMS)."""
        if not x_forwarded_for:
            logger.error(LogMessages.CLIENT_IP_MISSING)
            raise exceptions.ClientIpNotProvidedError

        if await GenerateOtpService._is_ip_blocked(
            redis_client,
            x_forwarded_for,
            receiver,
        ):
            logger.warning(LogMessages.IP_BLOCKED.format(x_forwarded_for))
            raise exceptions.IpBlockedError

        req_count = await GenerateOtpService._increment_otp_request(
            redis_client,
            x_forwarded_for,
            receiver,
        )
        logger.debug(
            LogMessages.OTP_REQ_COUNT.format(x_forwarded_for, receiver, req_count),
        )

        if req_count > 3:
            logger.warning(
                LogMessages.TOO_MANY_REQUESTS_BLOCKING.format(
                    x_forwarded_for,
                    receiver,
                ),
            )
            block_ip_for_24_hours.apply_async(
                queue=CeleryQueues.BLOCK_IP_QUEUE,
                args=([x_forwarded_for, receiver]),
            )
            raise exceptions.OtpTooManyAttemptsError

        receiver_for_key = str(receiver).lstrip("+")
        redis_key = CacheKeyTemplates.OTP_MOBILE.format(
            receiver=receiver_for_key,
            intent=intent,
        )
        await redis_client.setex(redis_key, CacheTTL.OTP_EXPIRY, otp)

        sms_payload = {
            RequestParams.MOBILE: mobile or receiver,
            RequestParams.CALLING_CODE: calling_code or "",
            CommParams.MESSAGE: None,
            CommParams.VARIABLES: {
                TemplateParams.OTP: otp,
                CommParams.VAR: otp,
            },
        }

        try:
            response = await call_communication_api(deeplinks.SMS_SEND_URL, sms_payload)
            if response and response.get(CommParams.STATUS) != ResponseParams.SUCCESS:
                logger.error(LogMessages.SMS_SEND_FAILED.format(response))
        except Exception as e:
            logger.error(LogMessages.SMS_SEND_EXCEPTION.format(e))

    @staticmethod
    async def _get_username(
        receiver: str,
        db_session: Optional[AsyncSession],
    ) -> str:
        """Retrieve user's first name from database if available."""
        username = receiver.split("@")[0]
        if db_session:
            user_rows = await execute_query(
                query=UserQueries.GET_USERNAME_BY_EMAIL,
                params={RequestParams.EMAIL: receiver},
                db_session=db_session,
            )
            if user_rows and user_rows[0].firstname:
                username = user_rows[0].firstname
        return username

    @staticmethod
    async def _get_forgot_password_payload(
        receiver: str,
        otp: str,
        db_session: Optional[AsyncSession],
    ) -> Dict[str, Any]:
        """Generate payload for forgot password email."""
        template_id = settings.brevo_forgot_password_template_id
        if template_id:
            username = await GenerateOtpService._get_username(receiver, db_session)
            return {
                CommParams.RECIPIENTS: [receiver],
                CommParams.TEMPLATE_ID: int(template_id),
                CommParams.TEMPLATE_PARAMS: {
                    TemplateParams.VAR: otp,
                    TemplateParams.USERNAME: username,
                    TemplateParams.RESET_URL: settings.brevo_reset_url,
                },
            }
        return {
            CommParams.RECIPIENTS: [receiver],
            CommParams.SUBJECT: EmailSubjects.RESET_PASSWORD,
            CommParams.MESSAGE: EmailMessages.RESET_PASSWORD.format(otp),
        }

    @staticmethod
    async def _get_resend_payload(
        receiver: str,
        otp: str,
        intent: str,
        db_session: Optional[AsyncSession],
    ) -> Dict[str, Any]:
        """Generate payload for resending OTP email."""
        template_id = settings.brevo_otp_resend_template_id
        if not template_id:
            raise Exception(LogMessages.BREVO_TEMPLATE_NOT_CONFIGURED)

        username = await GenerateOtpService._get_username(receiver, db_session)
        return {
            CommParams.RECIPIENTS: [receiver],
            CommParams.TEMPLATE_ID: int(template_id),
            CommParams.TEMPLATE_PARAMS: {
                TemplateParams.OTP_CODE: otp,
                TemplateParams.USERNAME: username,
            },
        }

    @staticmethod
    async def _get_registration_payload(
        receiver: str,
        otp: str,
        intent: str,
        db_session: Optional[AsyncSession],
    ) -> Dict[str, Any]:
        """Generate payload for registration/verification email."""
        template_id = settings.brevo_email_verification_template_id
        if template_id:
            username = await GenerateOtpService._get_username(receiver, db_session)
            return {
                CommParams.RECIPIENTS: [receiver],
                CommParams.TEMPLATE_ID: int(template_id),
                CommParams.TEMPLATE_PARAMS: {
                    TemplateParams.OTP_CODE: otp,
                    TemplateParams.USERNAME: username,
                },
            }
        return {
            CommParams.RECIPIENTS: [receiver],
            CommParams.SUBJECT: EmailSubjects.ONE_TIME_PASSWORD,
            CommParams.MESSAGE: EmailMessages.ONE_TIME_PASSWORD.format(otp),
        }
