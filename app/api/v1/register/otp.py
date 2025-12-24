import os
import random
import string

from app.api.queries import UserQueries
from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.deeplinks import *
from app.api.v1.register.task import block_ip_for_24_hours
from app.core.exceptions import (
    exceptions,  # as core_exceptions (keeping name 'exceptions' to match usage)
)
from app.db.utils import execute_query


class GenerateOtpService(object):

    @staticmethod
    async def _is_ip_blocked(redis_client, ip_address, receiver):
        val = await redis_client.get(f"blocked_ip_{ip_address}_{receiver}")
        return val is not None

    @staticmethod
    async def _increment_otp_request(redis_client, ip_address, receiver):
        key = f"otp_reqcount_{ip_address}_{receiver}"
        try:
            count = await redis_client.incr(key)
            # Always reset expiry to 180 seconds on every request
            await redis_client.expire(key, 180)
            return count
        except Exception as e:
            print(
                f"Redis error during OTP increment for {ip_address}_{receiver}: {e!s}",
            )
            raise exceptions.RedisServerDown()

    @staticmethod
    async def generate_otp(
        redis_client,
        receiver,
        receiver_type,
        intent,
        x_forwarded_for=None,
        is_resend=False,
        db_session=None,
    ):
        if receiver_type == "email":
            otp = "".join(random.choice(string.digits) for _ in range(4))
            # redis.set_val(f"email_otp_{receiver}_{intent}", otp, timeout=180)
            await redis_client.setex(f"email_otp_{receiver}_{intent}", 180, otp)
            try:
                # Use Brevo templates for different intents
                if intent == "forgot_password":
                    template_id = os.environ.get("BREVO_FORGOT_PASSWORD_TEMPLATE_ID")
                    reset_url = os.environ.get(
                        "BREVO_RESET_URL", "https://dev.erosuniverse.com/forgotPwd",
                    )
                    print(f"DEBUG: Intent={intent}, Template ID={template_id}")
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
                            "recipients": [receiver],
                            "template_id": int(template_id),
                            "template_params": {
                                "var": otp,
                                "username": username,
                                "reset_url": reset_url,
                            },
                        }
                        print(f"DEBUG: Using Brevo template payload: {payload}")
                    else:
                        # Fallback to regular email
                        payload = {
                            "recipients": [receiver],
                            "subject": "Reset Your Password - OTP",
                            "message": f"{otp} is your one time password to reset your ErosUniverse account password. It is valid for 3 minutes.",
                        }
                elif is_resend:
                    # Use Brevo template ID 11 for OTP resend
                    template_id = os.environ.get("BREVO_OTP_RESEND_TEMPLATE_ID")
                    if not template_id:
                        raise Exception("BREVO_OTP_RESEND_TEMPLATE_ID not configured")
                    print(f"DEBUG: Resend Intent={intent}, Template ID={template_id}")

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
                        "recipients": [receiver],
                        "template_id": int(template_id),
                        "template_params": {
                            "otp_code": otp,
                            "username": username,
                        },
                    }
                    print(f"DEBUG: Using Brevo resend template payload: {payload}")
                elif intent in ["email_verification", "registration"]:
                    # Use Brevo template ID 10 for email verification/registration
                    template_id = os.environ.get(
                        "BREVO_EMAIL_VERIFICATION_TEMPLATE_ID", "10",
                    )
                    print(f"DEBUG: Intent={intent}, Template ID={template_id}")
                    # Get actual username from User model
                    username = receiver.split("@")[0]

                    payload = {
                        "recipients": [receiver],
                        "template_id": int(template_id),
                        "template_params": {
                            "otp_code": otp,
                            "username": username,
                        },
                    }
                    print(
                        f"DEBUG: Using Brevo email verification template payload: {payload}",
                    )
                else:
                    # For other intents, use regular email format
                    payload = {
                        "recipients": [receiver],
                        "subject": "One Time Password.",
                        "message": f"{otp} is your one time password to set up your ErosUniverse account. It is valid for 3 minutes.",
                    }
                call_communication_api(MAIL_SEND_URL, payload)
            except Exception as e:
                print(f"Failed to send OTP email via CommService: {e!s}")
                raise exceptions.CommServiceAPICallFailed()
            return

        # Original logic for non-email flows
        if receiver_type == "mobile":
            if not x_forwarded_for:
                print("Client IP (x_forwarded_for) Missing")
                raise exceptions.ClientIpNotProvided()

            if await GenerateOtpService._is_ip_blocked(
                redis_client, x_forwarded_for, receiver,
            ):
                print(f"IP is blocked: {x_forwarded_for}")
                raise exceptions.IpBlocked()

            req_count = await GenerateOtpService._increment_otp_request(
                redis_client, x_forwarded_for, receiver,
            )
            print(f"OTP request count for {x_forwarded_for}_{receiver}: {req_count}")

            if req_count > 3:
                print(
                    f"Too many OTP requests, blocking IP: {x_forwarded_for}_{receiver}",
                )
                block_ip_for_24_hours.apply_async(
                    queue="block_ip_queue",
                    args=([x_forwarded_for, receiver]),
                )
                raise exceptions.OtpTooManyAttempts()

        payload = {
            "receiver": receiver,
            "receiver_type": receiver_type,
            "intent": intent,
        }

        response = call_communication_api(GENERATE_OTP_URL, payload)
        if "status" in response and response["status"] == "success":
            is_otp_sent = response["data"]
            if not is_otp_sent:
                print("OTP not sent")
                raise exceptions.OtpTooManyAttempts()
