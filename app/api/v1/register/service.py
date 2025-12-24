import logging
import smtplib
import socket
import time
import traceback
from asyncio.log import logger

import dns.resolver

from app.api.v1.register import deeplinks
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.deeplinks import *
from app.api.v1.register.otp import GenerateOtpService
from app.api.v1.register.redis import *
from app.core.constants import Intent
from app.core.exceptions.exceptions import (
    CommServiceAPICallFailed,
    ForgotPassword,
    MobileInvalid,
)

logger = logging.getLogger("django")

from app.api.queries import UserQueries
from app.db.utils import execute_query


class MobileVerificationService(object):
    @staticmethod
    def mobile_verification_service(mobile, calling_code):
        payload = {
            "mobile_number": mobile,
            "calling_code": calling_code,
        }
        response = call_communication_api(deeplinks.MOBILE_VERIFY_URL, payload)
        if "status" in response and response["status"] == "success":
            if not response["data"]["is_valid"]:
                raise MobileInvalid("Mobile number is not valid.")
        else:
            raise CommServiceAPICallFailed()

class EmailDnsVerifyService(object):
    def __init__(self, email="", show_support_message=False):
        self.show_support_message = show_support_message
        self.email = email
        self.email_domain = self.email.split("@")[1] if "@" in self.email else ""

    def verify(self):
        start_time = time.time()
        try:
            if (not self.email) or (not self.email_domain) or redis.get_val("dns.invalid_domains.{0}".format(self.email_domain)):
                self.raise_exception("Invalid email domain")

            if self.email_domain in redis.smembers("dns.skip_domains_for_verification"):
                return

            if redis.get_val("dns.valid_emails.{0}".format(self.email)):
                return

            cached_exception = redis.get_val("dns.invalid_emails.{0}".format(self.email))
            if cached_exception:
                self.raise_exception(cached_exception)

            self.get_mx_record_for_domain()
            self.verify_smtp_session()
            self.cache_valid_email()
        finally:
            logger.info("Time for EmailDnsVerifyService", extra= {
                "time": "{0} seconds".format(time.time() - start_time),
                "data": self.email,
            })

    def cache_valid_email(self):
        redis.set_val("dns.valid_domains.{0}".format(self.email_domain), "true", settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)
        redis.set_val("dns.valid_emails.{0}".format(self.email), "true", settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)

    def get_mx_record_for_domain(self):
        try:
            # check mx record for email domain
            records = dns.resolver.query(self.email_domain, "MX")
            self.mxRecord = str(records[0].exchange)
            if (not self.mxRecord or self.mxRecord == "."):
                raise dns.resolver.NoAnswer
        except (dns.resolver.NXDOMAIN,
                dns.resolver.NoAnswer,
                dns.resolver.NoMetaqueries,
                dns.resolver.NoNameservers,
                dns.resolver.NoRootSOA,
                dns.resolver.NotAbsolute,
                dns.resolver.YXDOMAIN):
            redis.set_val(
                "dns.invalid_domains.{0}".format(self.email_domain),
                "true",
                settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)
            self.raise_exception("Invalid email domain")
        except Exception as e:
            logger.info("Unhandled exception for domain", extra= {
                "exception": str(e),
                "data": self.email_domain,
            })
            self.raise_exception("Invalid email domain")

    def verify_smtp_session(self):
        retry_count = 0

        while retry_count < 3:
            try:
                smtp = smtplib.SMTP(timeout = 3)
                smtp.connect(self.mxRecord)
                smtp_status = smtp.helo()[0]
                if smtp_status != 250:
                    smtp.quit()
                    self.process_invalid_smtp_response("Email doesn't exist")

                smtp.mail("")
                smtp_status = smtp.rcpt(self.email)[0]
                if smtp_status != 250:
                    smtp.quit()
                    self.process_invalid_smtp_response("Email doesn't exist")

                break
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, ConnectionResetError, socket.error) as exception:
                logger.error(
                    "UNABLE TO CONNECT SMTP SERVER",
                    extra = {
                        "smtp_error": {
                            "email": self.email,
                            "message": str(exception),
                            "traceback": "".join(traceback.format_tb(exception.__traceback__)),
                        },
                    },
                )

                if(retry_count == 2):
                    self.process_invalid_smtp_response("Email domain connection error")
            retry_count += 1

    def process_invalid_smtp_response(self, message):
        redis.set_val(
            "dns.invalid_emails.{0}".format(self.email),
            message,
            settings.CACHE_TIMEOUT_FOR_EMAIL_DNS)
        self.raise_exception(message)

    def raise_exception(self, message):
        if self.show_support_message:
            raise ForgotPassword(message)
        else:
            raise ForgotPassword(message)

class UserVerifyService(object):
    @staticmethod
    def _get_user_state(user, deeplink_params):
        deeplink_map = {
            "U001": deeplinks.LOGIN_SCREEN.format(deeplink_params),
            "U002": deeplinks.OTP_SCREEN.format(deeplink_params + "&intent=registration"),
        }
        user_status = "U001" if user else "U002"

        state = {
            "user_status": user_status,
            "redirect_url":  deeplink_map[user_status],
        }
        return state

    @staticmethod
    async def get_user_state_by_email(redis_client, email, db_session):
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
            # email_dns_verify_service = EmailDnsVerifyService(email=email, show_support_message=False)
            # email_dns_verify_service.verify()
            await GenerateOtpService.generate_otp(redis_client, email, "email", Intent.REGISTRATION, db_session=db_session)
        return UserVerifyService._get_user_state(user, "email={}".format(email))

    @staticmethod
    def get_user_by_email(email):
        user = user.objects.filter(email=email).first()
        return user

    @staticmethod
    def get_user_by_mobile(mobile, calling_code):
        user = user.objects.filter(mobile=mobile, calling_code=calling_code).first()
        return user

    @staticmethod
    async def get_user_state_by_mobile(redis_client, mobile, calling_code, x_forwarded_for, db_session):
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
            MobileVerificationService.mobile_verification_service(mobile, calling_code)
            await GenerateOtpService.generate_otp(redis_client, calling_code+mobile, "mobile", Intent.REGISTRATION, x_forwarded_for, db_session=db_session)
        return UserVerifyService._get_user_state(user, "mobile=+{}-{}".format(calling_code, mobile))
