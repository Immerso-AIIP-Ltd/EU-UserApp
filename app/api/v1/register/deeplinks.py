# A collection of deeplinks that are returned in the responses of some of the onboarding APIs
# TODO - update this after getting the actual values from frontend
from app.settings import settings

LOGIN_SCREEN = "erosnowapp://login?{}"
OTP_SCREEN = "erosnowapp://verify_otp?{}"
SET_PASSWORD = "erosnowapp://set_password?{}"
LINK_ACCOUNT =  "erosnowapp://link_account"

VERIFY_OTP_URL = settings.communication_api_url + "/api/v1/comm/otp/validate/"
GENERATE_OTP_URL = settings.communication_api_url + "/api/v1/comm/otp/generate/"
MAIL_SEND_URL = settings.communication_api_url + "/api/v1/comm/email/send/"
SMS_SEND_URL = settings.communication_api_url + "/api/v1/comm/sms/send/"
MOBILE_VERIFY_URL = settings.communication_api_url + "/api/v1/comm/sms/verify_mobile/"
FACEBOOOK_AUTH_LINK = "https://graph.facebook.com/oauth/access_token"
LEGACY_LOGIN = settings.legacy_api_url + "/api/v2/secured/user/login"
LEGACY_LOGOUT = settings.legacy_api_url + "/api/v2/secured/user/logout"
LEGACY_MAP_GCM = settings.legacy_api_url + "/api/v2/secured/user/mapgcm"
