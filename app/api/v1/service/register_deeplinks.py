# A collection of deeplinks that are returned in the responses of
# some of the onboarding APIs
# TODO - update this after getting the actual values from frontend
from app.settings import settings

LOGIN_SCREEN = settings.deeplink_login_screen
OTP_SCREEN = settings.deeplink_otp_screen
SET_PASSWORD = settings.deeplink_set_password
LINK_ACCOUNT = settings.deeplink_link_account

VERIFY_OTP_URL = settings.verify_otp_url
GENERATE_OTP_URL = settings.generate_otp_url
MAIL_SEND_URL = settings.mail_send_url
SMS_SEND_URL = settings.sms_send_url
MOBILE_VERIFY_URL = settings.mobile_verify_url
FACEBOOOK_AUTH_LINK = settings.facebook_auth_link
LEGACY_LOGIN = settings.legacy_login_url
LEGACY_LOGOUT = settings.legacy_logout_url
LEGACY_MAP_GCM = settings.legacy_map_gcm_url
