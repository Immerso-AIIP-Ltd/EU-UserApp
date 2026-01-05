import logging
import smtplib
import socket
import time
import traceback
from typing import Any
from asyncio.log import logger

from app.db.models.user_app import Device
import dns.resolver

from app.api.v1.register import deeplinks
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.deeplinks import *
from app.api.v1.register.otp import GenerateOtpService
from app.cache.utils import get_val, set_val, smembers
from app.core.constants import Intent
from app.core.exceptions.exceptions import (
    CommServiceAPICallFailed,
    ForgotPassword,
    MobileInvalid,
    DeviceAlreadyRegistered,
    DeviceNotRegistered,
)

logger = logging.getLogger("django")

from app.api.queries import UserQueries
from app.db.utils import execute_query


class MobileVerificationService(object):
    async def mobile_verification_service(mobile: str, calling_code: str) -> None:
        payload = {
            "mobile_number": mobile,
            "calling_code": calling_code,
        }
        response = await call_communication_api(deeplinks.MOBILE_VERIFY_URL, payload)
        # response should be awaited if call_communication_api is an async wrapper or handled properly
        # Assuming call_communication_api is SYNC here based on usage or needs AWAIT if async.
        # Previous context said it was made async.
        # But wait, MobileVerificationService seems unused or legacy?
        # Let's assume it needs await if call_communication_api is async.
        # However, call_communication_api was imported from commservice.
        if "status" in response and response["status"] == "success":
            if not response["data"]["is_valid"]:
                raise MobileInvalid("Mobile number is not valid.")
        else:
            raise CommServiceAPICallFailed()


class EmailDnsVerifyService(object):
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
        start_time = time.time()
        try:
            if (
                (not self.email)
                or (not self.email_domain)
                or await get_val(
                    self.redis_client,
                    "dns.invalid_domains.{0}".format(self.email_domain),
                )
            ):
                await self.raise_exception("Invalid email domain")

            # Check skip domains (awaiting smembers)
            skip_domains = await smembers(
                self.redis_client,
                "dns.skip_domains_for_verification",
            )
            if self.email_domain in skip_domains:
                return

            if await get_val(
                self.redis_client,
                "dns.valid_emails.{0}".format(self.email),
            ):
                return

            cached_exception = await get_val(
                self.redis_client,
                "dns.invalid_emails.{0}".format(self.email),
            )
            if cached_exception:
                await self.raise_exception(cached_exception)

            await self.get_mx_record_for_domain()
            await self.verify_smtp_session()
            await self.cache_valid_email()
        finally:
            logger.info(
                "Time for EmailDnsVerifyService",
                extra={
                    "time": "{0} seconds".format(time.time() - start_time),
                    "data": self.email,
                },
            )

    async def cache_valid_email(self) -> None:
        await set_val(
            self.redis_client,
            "dns.valid_domains.{0}".format(self.email_domain),
            "true",
            timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
        )
        await set_val(
            self.redis_client,
            "dns.valid_emails.{0}".format(self.email),
            "true",
            timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
        )

    async def get_mx_record_for_domain(self) -> None:
        try:
            # check mx record for email domain
            records = dns.resolver.query(self.email_domain, "MX")
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
                "dns.invalid_domains.{0}".format(self.email_domain),
                "true",
                timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
            )
            await self.raise_exception("Invalid email domain")
        except Exception as e:
            logger.info(
                "Unhandled exception for domain",
                extra={
                    "exception": str(e),
                    "data": self.email_domain,
                },
            )
            await self.raise_exception("Invalid email domain")

    async def verify_smtp_session(self) -> None:
        retry_count = 0

        while retry_count < 3:
            try:
                smtp = smtplib.SMTP(timeout=3)
                smtp.connect(self.mxRecord)
                smtp_status = smtp.helo()[0]
                if smtp_status != 250:
                    smtp.quit()
                    await self.process_invalid_smtp_response("Email doesn't exist")

                smtp.mail("")
                smtp_status = smtp.rcpt(self.email)[0]
                if smtp_status != 250:
                    smtp.quit()
                    await self.process_invalid_smtp_response("Email doesn't exist")

                break
            except (
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                ConnectionResetError,
                socket.error,
            ) as exception:
                logger.error(
                    "UNABLE TO CONNECT SMTP SERVER",
                    extra={
                        "smtp_error": {
                            "email": self.email,
                            "message": str(exception),
                            "traceback": "".join(
                                traceback.format_tb(exception.__traceback__),
                            ),
                        },
                    },
                )

                if retry_count == 2:
                    await self.process_invalid_smtp_response(
                        "Email domain connection error",
                    )
            retry_count += 1

    async def process_invalid_smtp_response(self, message: str) -> None:
        await set_val(
            self.redis_client,
            "dns.invalid_emails.{0}".format(self.email),
            message,
            timeout=settings.CACHE_TIMEOUT_FOR_EMAIL_DNS,
        )
        await self.raise_exception(message)

    async def raise_exception(self, message: str) -> None:
        if self.show_support_message:
            raise ForgotPassword(message)
        else:
            raise ForgotPassword(message)


class UserVerifyService(object):
    @staticmethod
    async def _get_user_state(user: Any, deeplink_params: str) -> dict[str, Any]:
        deeplink_map = {
            "U001": deeplinks.LOGIN_SCREEN.format(deeplink_params),
            "U002": deeplinks.OTP_SCREEN.format(
                deeplink_params + "&intent=registration",
            ),
        }
        user_status = "U001" if user else "U002"

        state = {
            "user_status": user_status,
            "redirect_url": deeplink_map[user_status],
        }
        return state

    @staticmethod
    async def get_user_state_by_email(
        redis_client: Any,
        email: str,
        db_session: Any,
    ) -> dict[str, Any]:
        user_rows = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                "email": email,
                "mobile": None,
                "calling_code": None,
            },
            db_session=db_session,
        )
        user = user_rows[0] if user_rows else None

        if not user:
            # email_dns_verify_service = EmailDnsVerifyService(redis_client, email=email, show_support_message=False)
            # await email_dns_verify_service.verify()
            await GenerateOtpService.generate_otp(
                redis_client,
                email,
                "email",
                Intent.REGISTRATION,
                db_session=db_session,
            )
        return UserVerifyService._get_user_state(user, "email={}".format(email))

    # @staticmethod
    # def get_user_by_email(email):
    #     user = user.objects.filter(email=email).first()
    #     return user

    # @staticmethod
    # def get_user_by_mobile(mobile, calling_code):
    #     user = user.objects.filter(mobile=mobile, calling_code=calling_code).first()
    #     return user

    @staticmethod
    async def get_user_state_by_mobile(
        redis_client: Any,
        mobile: str,
        calling_code: str,
        x_forwarded_for: str | None,
        db_session: Any,
    ) -> dict[str, Any]:
        user_rows = await execute_query(
            query=UserQueries.CHECK_USER_EXISTS,
            params={
                "email": None,
                "mobile": mobile,
                "calling_code": calling_code,
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
                receiver_type="mobile",
                intent=Intent.REGISTRATION,
                x_forwarded_for=x_forwarded_for,
                db_session=db_session,
                mobile=mobile,
                calling_code=calling_code,
            )
        return UserVerifyService._get_user_state(
            user,
            "mobile=+{}-{}".format(calling_code, mobile),
        )


class DeviceService(object):
    async def is_device_registered(device_id: str) -> bool:
        return await Device.objects.filter(device_id=device_id).exists()

    async def create_device(device_id: str, **attrs) -> None:
        if await DeviceService.is_device_registered(device_id):
            raise DeviceAlreadyRegistered()
        # make an entry in the new device table
        # switched to an att dict so that we have more flexibility into fields we accept
        device = Device(device_id=device_id, **attrs)
        device.save()

        # Log device creation
        user_uuid = attrs.get("uuid")
        logger.info(
            "Device registered",
            extra={
                "device_id": device_id,
                "user_uuid": user_uuid,
            },
        )

        return device

    async def get_device_attrs(device_id):
        if not await DeviceService.is_device_registered(device_id):
            raise DeviceNotRegistered()
        # return any one device row
        device = Device.objects.filter(device_id=device_id).last()
        device_attrs = {}
        for attr in ["device_type", "device_name", "device_id"]:
            device_attrs[attr] = getattr(device, attr)
        return device_attrs
