from utils import redis

from app.api.v1.register.commservice import call_communication_api
from app.api.v1.register.deeplinks import links
from app.core.constants import Intent
from app.core.exceptions.exceptions import (
    EmailNotRegistered,
    MobileNotRegistered,
    OtpInvalid,
)
from app.db.models.user_app import User


class VerifyOtpService(object):

    """@staticmethod
    def _get_redirect_url(intent, deeplink_params):
        state = {
            'redirect_url': deeplinks.SET_PASSWORD.format(deeplink_params)
        }
    return state
    """

    # @staticmethod
    # def verify_otp(receiver, receiver_type, otp, intent, deeplink_params):
    #     payload = {
    #         'receiver': receiver,
    #         'receiver_type': receiver_type,
    #         'intent': intent,
    #         'otp': otp
    #     }
    #     response = call_communication_api(
    #         links.VERIFY_OTP_URL, payload)
    #     if 'status' in response and response['status'] == 'success':
    #         is_verified = response['data']
    #         if is_verified:
    #             return VerifyOtpService._get_redirect_url(intent, deeplink_params)
    #         else:
    #             raise exceptions.InvalidOtp()

    @staticmethod
    def verify_otp(receiver, receiver_type, otp, intent, deeplink_params):
        if receiver_type == "email":
            key = f"email_otp_{receiver}_{intent}"
            stored = redis.get_val(key)
            if stored and str(stored) == str(otp):
                redis.remove_key(key)
                return VerifyOtpService._get_redirect_url(intent, deeplink_params)
            raise OtpInvalid()

        # For non-email flows, use CommService validation
        payload = {
            "receiver": receiver,
            "receiver_type": receiver_type,
            "intent": intent,
            "otp": otp,
        }
        response = call_communication_api(
            links.VERIFY_OTP_URL, payload)
        if "status" in response and response["status"] == "success":
            is_verified = response["data"]
            if is_verified:
                return VerifyOtpService._get_redirect_url(intent, deeplink_params)
            else:
                raise OtpInvalid()

    @staticmethod
    def verify_email_user_exist(user):
        if not User.objects.filter(email=user).exists():
            raise EmailNotRegistered()

    @staticmethod
    def verify_mobile_user_exist(mobile, calling_code):
        if not User.objects.filter(mobile=mobile, calling_code=calling_code).exists():
            raise MobileNotRegistered()

    @staticmethod
    def derive_intent(email=None, mobile=None, calling_code=None):
        """
        In case of set password or forget password, the frontend will pass us just the OTP
        and not the intent. But we can derive the intent based on whether the user exists in our db
        or not.
        """
        if email and User.objects.filter(email=email).exists():
            return Intent.FORGOT_PASSWORD
        if mobile and calling_code and User.objects.filter(mobile=mobile, calling_code=calling_code).exists():
            return Intent.FORGOT_PASSWORD
        return Intent.REGISTRATION
