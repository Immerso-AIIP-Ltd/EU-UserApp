import logging
import smtplib
import socket
import time
import traceback
from typing import Any

import dns.resolver
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.queries import UserQueries
from app.api.v1.service import register_deeplinks
from app.api.v1.service.register_commservice import call_communication_api
from app.api.v1.service.register_otp import GenerateOtpService
from app.cache.utils import get_val, set_val, smembers
from app.core.constants import (
    CacheValues,
    CommParams,
    DeepLinkParamFormats,
    DnsRecordTypes,
    EmailVerificationCacheKeys,
    ErrorMessages,
    Intents,
    LogKeys,
    RequestParams,
    ResponseParams,
    ServiceLogMessages,
    UserStates,
)
from app.core.exceptions.exceptions import (
    CommServiceAPICallFailedError,
    DeviceAlreadyRegisteredError,
    DeviceNotRegisteredError,
    ForgotPasswordError,
    MobileInvalidError,
)
from app.db.utils import execute_query
from app.settings import settings

logger = logging.getLogger(__name__)


class MobileVerificationService:
    """Service to handle mobile number verification via external API."""

    @staticmethod
    async def mobile_verification_service(mobile: str, calling_code: str) -> None:
        """Verify mobile number validity using external communication service."""
        payload = {
            RequestParams.MOBILE_NUMBER: mobile,
            RequestParams.CALLING_CODE: calling_code,
        }
        response = await call_communication_api(
            register_deeplinks.MOBILE_VERIFY_URL,
            payload,
        )
        # response should be awaited if call_communication_api is an async wrapper
        # or handled properly
        # Assuming call_communication_api is SYNC here based on usage or needs
        # AWAIT if async.
        # Previous context said it was made async.
        # But wait, MobileVerificationService seems unused or legacy?
        # Let's assume it needs await if call_communication_api is async.
        # However, call_communication_api was imported from commservice.
        if (
            CommParams.STATUS in response
            and response[CommParams.STATUS] == ResponseParams.SUCCESS
        ):
            if not response[ResponseParams.DATA][RequestParams.IS_VALID]:
                raise MobileInvalidError(ErrorMessages.MOBILE_INVALID)
        else:
            raise CommServiceAPICallFailedError


class EmailDnsVerifyService:
    """Service to verify email validity via DNS and SMTP checks."""

    def __init__(
        self,
        redis_client: Any,
        email: str = "",
        show_support_message: bool = False,
    ) -> None:
        self.redis_client = redis_client
        self.show_support_message = show_support_message
        self.email = email
        self.email_domain = self.email.split("@")[1] if "@" in self.email else ""

    async def verify(self) -> None:
        """Perform full email verification (Cache -> DNS -> SMTP)."""
        start_time = time.time()
        try:
            if (
                (not self.email)
                or (not self.email_domain)
                or await get_val(
                    self.redis_client,
                    EmailVerificationCacheKeys.DNS_INVALID_DOMAINS.format(
                        self.email_domain,
                    ),
                )
            ):
                await self.raise_exception(ErrorMessages.INVALID_EMAIL_DOMAIN)

            # Check skip domains (awaiting smembers)
            skip_domains = await smembers(
                self.redis_client,
                EmailVerificationCacheKeys.DNS_SKIP_DOMAINS,
            )
            if self.email_domain in skip_domains:
                return

            if await get_val(
                self.redis_client,
                EmailVerificationCacheKeys.DNS_VALID_EMAILS.format(self.email),
            ):
                return

            cached_exception = await get_val(
                self.redis_client,
                EmailVerificationCacheKeys.DNS_INVALID_EMAILS.format(self.email),
            )
            if cached_exception:
                await self.raise_exception(cached_exception)

            await self.get_mx_record_for_domain()
            await self.verify_smtp_session()
            await self.cache_valid_email()
        finally:
            logger.info(
                ServiceLogMessages.LOG_TIME,
                extra={
                    LogKeys.TIME: "{0} seconds".format(time.time() - start_time),
                    LogKeys.DATA: self.email,
                },
            )

    async def cache_valid_email(self) -> None:
        """Cache successful email verification result in Redis."""
        await set_val(
            self.redis_client,
            EmailVerificationCacheKeys.DNS_VALID_DOMAINS.format(self.email_domain),
            CacheValues.TRUE,
            timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
        )
        await set_val(
            self.redis_client,
            EmailVerificationCacheKeys.DNS_VALID_EMAILS.format(self.email),
            CacheValues.TRUE,
            timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
        )

    async def get_mx_record_for_domain(self) -> None:
        """Query DNS for MX records of the email domain."""
        try:
            # check mx record for email domain
            records = dns.resolver.query(self.email_domain, DnsRecordTypes.MX)
            self.mxRecord = str(records[0].exchange)
            if not self.mxRecord or self.mxRecord == ".":
                raise dns.resolver.NoAnswer
        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.resolver.NoMetaqueries,
            dns.resolver.NoNameservers,
            dns.resolver.NoRootSOA,
            dns.resolver.NotAbsolute,
            dns.resolver.YXDOMAIN,
        ):
            await set_val(
                self.redis_client,
                EmailVerificationCacheKeys.DNS_INVALID_DOMAINS.format(
                    self.email_domain,
                ),
                CacheValues.TRUE,
                timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
            )
            await self.raise_exception(ErrorMessages.INVALID_EMAIL_DOMAIN)
        except Exception as e:
            logger.info(
                ServiceLogMessages.UNHANDLED_EXCEPTION_DOMAIN,
                extra={
                    LogKeys.EXCEPTION: str(e),
                    LogKeys.DATA: self.email_domain,
                },
            )
            await self.raise_exception(ErrorMessages.INVALID_EMAIL_DOMAIN)

    async def verify_smtp_session(self) -> None:
        """Attempt to establish an SMTP session to verify mailbox existence."""
        retry_count = 0

        while retry_count < 3:
            try:
                smtp = smtplib.SMTP(timeout=3)
                smtp.connect(self.mxRecord)
                smtp_status = smtp.helo()[0]
                if smtp_status != 250:
                    smtp.quit()
                    await self.process_invalid_smtp_response(
                        ErrorMessages.EMAIL_DOES_NOT_EXIST,
                    )

                smtp.mail("")
                smtp_status = smtp.rcpt(self.email)[0]
                if smtp_status != 250:
                    smtp.quit()
                    await self.process_invalid_smtp_response(
                        ErrorMessages.EMAIL_DOES_NOT_EXIST,
                    )

                break
            except (
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                ConnectionResetError,
                socket.error,
            ) as exception:
                logger.error(
                    ServiceLogMessages.UNABLE_TO_CONNECT_SMTP,
                    extra={
                        LogKeys.SMTP_ERROR: {
                            LogKeys.EMAIL: self.email,
                            LogKeys.MESSAGE: str(exception),
                            LogKeys.TRACEBACK: "".join(
                                traceback.format_tb(exception.__traceback__),
                            ),
                        },
                    },
                )

                if retry_count == 2:
                    await self.process_invalid_smtp_response(
                        ErrorMessages.EMAIL_DOMAIN_CONNECTION_ERROR,
                    )
            retry_count += 1

    async def process_invalid_smtp_response(self, message: str) -> None:
        """Cache invalid email result and raise exception."""
        await set_val(
            self.redis_client,
            EmailVerificationCacheKeys.DNS_INVALID_EMAILS.format(self.email),
            message,
            timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
        )
        await self.raise_exception(message)

    async def raise_exception(self, message: str) -> None:
        """Helper to raise ForgotPasswordError."""
        raise ForgotPasswordError(message)


class UserVerifyService:
    """Service to verify user registration state and initiate OTP flows."""

    @staticmethod
    async def _get_user_state(user: Any, deeplink_params: str) -> dict[str, Any]:
        deeplink_map = {
            UserStates.U001: register_deeplinks.LOGIN_SCREEN.format(deeplink_params),
            UserStates.U002: register_deeplinks.OTP_SCREEN.format(
                deeplink_params + DeepLinkParamFormats.REGISTRATION_INTENT,
            ),
        }
        user_status = UserStates.U001 if user else UserStates.U002

        return {
            ResponseParams.USER_STATUS: user_status,
            ResponseParams.REDIRECT_URL: deeplink_map[user_status],
        }

    @staticmethod
    async def get_user_state_by_email(
        redis_client: Any,
        email: str,
        db_session: Any,
    ) -> dict[str, Any]:
        """Check if user exists by email and start registration OTP if not."""
        user_rows = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                RequestParams.EMAIL: email,
                RequestParams.MOBILE: None,
                RequestParams.CALLING_CODE: None,
            },
            db_session=db_session,
        )
        user = user_rows[0] if user_rows else None

        if not user:
            await GenerateOtpService.generate_otp(
                redis_client,
                email,
                RequestParams.EMAIL,
                Intents.REGISTRATION,
                db_session=db_session,
            )
        return await UserVerifyService._get_user_state(
            user,
            DeepLinkParamFormats.EMAIL.format(email),
        )

    @staticmethod
    async def get_user_state_by_mobile(
        redis_client: Any,
        mobile: str,
        calling_code: str,
        x_forwarded_for: str | None,
        db_session: Any,
    ) -> dict[str, Any]:
        """Verify user state and generate OTP if user doesn't exist."""
        user_rows = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                RequestParams.EMAIL: None,
                RequestParams.MOBILE: mobile,
                RequestParams.CALLING_CODE: calling_code,
            },
            db_session=db_session,
        )
        user = user_rows[0] if user_rows else None

        if not user:
            await MobileVerificationService.mobile_verification_service(
                mobile,
                calling_code,
            )
            await GenerateOtpService.generate_otp(
                redis_client=redis_client,
                receiver=calling_code + mobile,
                receiver_type=RequestParams.MOBILE,
                intent=Intents.REGISTRATION,
                x_forwarded_for=x_forwarded_for,
                db_session=db_session,
                mobile=mobile,
                calling_code=calling_code,
            )
        return await UserVerifyService._get_user_state(
            user,
            DeepLinkParamFormats.MOBILE.format(calling_code, mobile),
        )


class DeviceService:
    """Service to handle device registration and retrieval."""

    @staticmethod
    async def is_device_registered(device_id: str, db_session: AsyncSession) -> bool:
        """Check if a device is already registered in the database."""
        rows = await execute_query(
            query=UserQueries.CHECK_DEVICE_EXISTS,
            params={RequestParams.DEVICE_ID: device_id},
            db_session=db_session,
        )
        return bool(rows)

    @staticmethod
    async def create_device(
        device_id: str,
        db_session: AsyncSession,
        **attrs: Any,
    ) -> None:
        """Register a new device in the database."""
        if await DeviceService.is_device_registered(device_id, db_session):
            raise DeviceAlreadyRegisteredError

        params = {
            RequestParams.DEVICE_ID: device_id,
            RequestParams.USER_ID: attrs.get(RequestParams.UUID),
            RequestParams.DEVICE_NAME: attrs.get(RequestParams.DEVICE_NAME),
            RequestParams.DEVICE_TYPE: attrs.get(RequestParams.DEVICE_TYPE),
            RequestParams.PLATFORM: attrs.get(RequestParams.PLATFORM),
            RequestParams.USER_TOKEN: attrs.get(RequestParams.USER_TOKEN),
        }
        await execute_query(
            query=UserQueries.INSERT_DEVICE,
            params=params,
            db_session=db_session,
        )
        await db_session.commit()

        logger.info(
            ServiceLogMessages.DEVICE_REGISTERED,
            extra={
                RequestParams.DEVICE_ID: device_id,
                RequestParams.USER_ID: attrs.get(RequestParams.UUID),
            },
        )

    @staticmethod
    async def get_device_attrs(
        device_id: str,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """Retrieve device attributes by its ID."""
        if not await DeviceService.is_device_registered(device_id, db_session):
            raise DeviceNotRegisteredError

        rows = await execute_query(
            query=UserQueries.GET_DEVICE_BY_ID,
            params={RequestParams.DEVICE_ID: device_id},
            db_session=db_session,
        )
        if not rows:
            return {}

        device = rows[0]
        device_attrs = {}
        for attr in [
            RequestParams.DEVICE_TYPE,
            RequestParams.DEVICE_NAME,
            RequestParams.DEVICE_ID,
        ]:
            device_attrs[attr] = device.get(attr)
        return device_attrs
