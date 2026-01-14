"""Application constants."""


# General
class AppUserApp:
    """Application configuration."""

    NAME = "EU-UserApp"
    VERSION = "1.0.0"
    REDIS_MAX_CONNECTIONS = 100
    REDIS_SOCKET_CONNECT_TIMEOUT = 5
    REDIS_SOCKET_KEEPALIVE = True
    REDIS_TCP_KEEPIDLE = 60
    REDIS_TCP_KEEPINTVL = 30
    REDIS_TCP_KEEPCNT = 4
    REDIS_RETRY_ON_TIMEOUT = True
    REDIS_HEALTH_CHECK_INTERVAL = 10
    REDIS_DECODE_RESPONSES = True


# HTTP Status Codes
class HTTPStatus:
    """HTTP status codes."""

    OK = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500
    UNAUTHORIZED = 401
    FORBIDDEN = 403


class HTTPMethods:
    """HTTP methods."""

    POST = "POST"
    GET = "GET"


class HeaderValues:
    """HTTP header values."""

    APPLICATION_JSON = "application/json"
    APPLICATION_FORM_URLENCODED = "application/x-www-form-urlencoded"


class CommServiceConfig:
    """Communication service configuration."""

    TIMEOUT = 10
    LOGGER_MSG = "COMM API CALL"


class LogKeys:
    """Keys for structured logging."""

    SERVER_RESPONSE = "server_response"
    SERVER_RESPONSE_CODE = "server_response_code"
    TIME = "time"
    EXCEPTION = "exception"
    SMTP_ERROR = "smtp_error"
    TRACEBACK = "traceback"
    DATA = "data"
    EMAIL = "email"
    MESSAGE = "message"


class CacheKeyTemplates:
    """Cache key templates for all endpoints."""

    CONFIGURATIONS = "configurations:all:{platform}:{appname}:{api_version}"
    CACHE_KEY_DEVICE_INVITE_STATUS = (
        "device:invite:status:{device_id}:{platform}:{country}:{version}"
    )
    CACHE_KEY_DEVICE_INVITE = (
        "device:invite:{device_id}:{coupon_id}:{platform}:{version}:{country}"
    )
    CACHE_KEY_REGISTRATION_DATA = "registration:data:{identifier}"
    CACHE_KEY_USER_PROFILE = (
        "user_profile:{user_id}:platform:{platform}:version:{version}:country:{country}"
    )
    OTP_EMAIL = "email_otp_{receiver}_{intent}"
    OTP_MOBILE = "mobile_otp_{receiver}_{intent}"
    BLOCKED_IP = "blocked_ip_{ip_address}_{receiver}"
    OTP_REQ_COUNT = "otp_reqcount_{ip_address}_{receiver}"
    USER_AUTH_TOKEN = "auth:{user_uuid}:{device_id}"  # noqa: S105


class CacheTTL:
    """Cache Time-To-Live (TTL) values in seconds."""

    TTL_FAST = 900  # 15 minutes
    TTL_STANDARD = 3600  # 1 hour
    TTL_EXTENDED = 43200  # 12 hours
    TTL_MAX = 86400  # 24 hours
    TTL_INVITE_DEVICE = 60
    TTL_USER_PROFILE = 3600
    OTP_EXPIRY = 180
    TOKEN_EXPIRY = 3600  # 1 hour


class QueryTimeouts:
    """Database query timeout values in seconds."""

    TIMEOUT_FAST = 1.0
    TIMEOUT_STANDARD = 3.0
    TIMEOUT_EXTENDED = 5.0


class RequestParams:
    """Request parameter names."""

    PLATFORM = "platform"
    APPNAME = "appname"
    API_VERSION = "api_version"
    USER_ID = "user_id"
    PAGE = "page"
    PAGES = "pages"
    LIMIT = "limit"
    OFFSET = "offset"
    LANGUAGE = "language"
    COUNTRY_CODE = "country_code"
    LANGUAGE_KEY = "language_key"
    TEXT_KEY = "text_key"
    LANGUAGE_CODE = "language_code"
    ACTIVE = "active"
    TRANSLATIONS = "translations"
    DATA = "data"
    TRANSLATED_TEXT = "translated_text"
    EMAIL = "email"
    MOBILE = "mobile"
    X_DEVICE_ID = "x-device-id"
    X_FORWARD_FOR = "x-forward-for"
    X_FORWARDED_FOR = "x-forwarded-for"
    COUNTRY = "country"
    DEVICE_ID = "device_id"
    COUPON_ID = "coupon_id"
    CALLING_CODE = "calling_code"
    NAME = "name"
    INVITED_LIST = "invited_list"
    OTP = "otp"
    IS_VERIFIED = "is_verified"
    QUEUE_NUMBER = "queue_number"
    STATUS = "status"
    SENT = "sent"
    INVITED = "invited"
    DUPLICATES = "duplicates"
    INVALID = "invalid"
    FAILED = "failed"
    DEVICE = "Device"
    DEVICE_NAME = "device_name"
    DEVICE_TYPE = "device_type"
    OTP_VERIFIED = "otp_verified"
    INVITER_ID = "inviter_id"
    INVITED_EMAIL = "invited_email"
    INVITED_MOBILE = "invited_mobile"
    INVITED_CALLING_CODE = "invited_calling_code"
    INVITED_USER_ID = "invited_user_id"
    WAITLIST_ID = "waitlist_id"
    API_CLIENT = "api_client"
    TOKEN = "token"  # noqa: S105
    TOKEN_EXPIRY = "token_expiry"  # noqa: S105
    USER_TOKEN = "user_token"  # noqa: S105
    JSON = "json"
    LOCALHOST = "127.0.0.1"
    MOBILE_NUMBER = "mobile_number"
    EMAIL_ADDRESS = "email_address"
    AUTH_TOKEN = "auth_token"  # noqa: S105
    REFRESH_TOKEN = "refresh_token"  # noqa: S105
    AUTH_TOKEN_EXPIRY = "auth_token_expiry"  # noqa: S105
    IMAGE = "image"
    USER = "user"
    APP_VERSION = "app_version"
    VERSION = "version"
    GENDER = "gender"
    ABOUT_ME = "about_me"
    BIRTH_DATE = "birth_date"
    NICK_NAME = "nick_name"
    AVATAR_ID = "avatar_id"
    PROFILE_IMAGE = "profile_image"
    IS_VALID = "is_valid"
    UUID = "uuid"
    KID = "kid"
    EXP = "exp"
    PARTNER_ID = "partner_id"
    CLIENT_ID = "client_id"
    CLIENT_SECRET = "client_secret"  # noqa: S105
    PUSH_TOKEN = "push_token"  # noqa: S105
    DEVICE_IP = "device_ip"
    IS_VPN = "is_vpn"
    IS_ANONYMOUS_PROXY = "is_anonymous_proxy"
    RESIDENCY_VERIFIED = "residency_verified"
    IS_ROOTED = "is_rooted"
    IS_JAILBROKEN = "is_jailbroken"
    DEVICE_ACTIVE = "device_active"
    DRM_TYPE = "drm_type"
    HARDWARE_ENCRYPTION = "hardware_encryption"
    TRANSACTION_TYPE = "transaction_type"
    IS_IP_LEGAL = "is_ip_legal"
    NATIVE_TOKEN = "native_token"  # noqa: S105
    DATE_DEACTIVATED = "date_deactivated"
    UNKNOWN_DEVICE = "unknown_device"
    FIRSTNAME = "firstname"
    LASTNAME = "lastname"
    IMAGE_URL = "image_url"


class DnsRecordTypes:
    """DNS record types."""

    MX = "MX"


class PlatformTypes:
    """Platform types."""

    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class DeviceTypes:
    """Device types."""

    MOBILE = "mobile"
    DESKTOP = "desktop"


class UserAgentSubstrings:
    """User agent substrings for device detection."""

    ANDROID = "android"
    IPHONE = "iphone"
    IPAD = "ipad"
    WINDOWS = "windows"
    MACINTOSH = "macintosh"
    CHROME = "chrome"
    EDG = "edg"
    FIREFOX = "firefox"


class DeviceNames:
    """Device names."""

    ANDROID_DEVICE = "Android Device"
    IPHONE = "iPhone"
    WINDOWS_BROWSER = "Windows Browser"
    MAC_BROWSER = "Mac Browser"
    WEB_BROWSER = "Web Browser"
    CHROME = " Chrome"
    EDGE = " Edge"
    FIREFOX = " Firefox"
    UNKNOWN_DEVICE = "unknown_device"
    BOOTSTRAP_DEVICE = "Bootstrap Device"


class SocialProviders:
    """Social login providers."""

    APPLE = "apple"
    GOOGLE = "google"
    FACEBOOK = "facebook"


class CacheValues:
    """Common cache values."""

    TRUE = "true"
    EROS = "EROS"


class DeepLinkParamFormats:
    """Formats for deep link parameters."""

    EMAIL = "email={}"
    MOBILE = "mobile=+{}-{}"
    REGISTRATION_INTENT = "&intent=registration"


class ProcessParams:
    """Process parameter names."""

    IS_CONSUMED = "is_consumed"
    IS_EXPIRED = "is_expired"
    ID = "id"
    OTP_RESENT = "otp_resent"
    OTP_SENT = "otp_sent"
    USER = "user"
    MODEL_DUMP = "model_dump"
    EMAIL_ADDRESS = "email address"
    MOBILE_NUMBER = "mobile number"
    REG_ACCESS_TOKEN = "accesstoken"  # noqa: S105
    REG_REFRESH_TOKEN = "refreshtoken"  # noqa: S105


class ResponseParams:
    """Response field names."""

    # Top-level response fields
    SUCCESS = "success"
    MESSAGE = "message"
    DATA = "data"
    META = "meta"
    ERROR = "error"
    VERIFICATION_SUCCESS = "verification_success"
    VERIFIED = "verified"

    # Meta fields
    API_VERSION = "api_version"
    TIMESTAMP = "timestamp"
    REQUEST_ID = "request_id"
    TOTAL_RECORDS = "total_records"
    PAGE = "page"
    PER_PAGE = "per_page"
    TOTAL_PAGES = "total_pages"
    USER_STATUS = "user_status"
    REDIRECT_URL = "redirect_url"

    # Error fields (if needed)
    ERROR_CODE = "error_code"
    ERROR_DETAILS = "error_details"


class CommParams:
    """Communication payload parameter names."""

    RECIPIENTS = "recipients"
    SUBJECT = "subject"
    MESSAGE = "message"
    HTML_CONTENT = "html_content"
    TEMPLATE_ID = "template_id"
    TEMPLATE_PARAMS = "template_params"
    VARIABLES = "variables"
    INTENT = "intent"
    VAR = "var"
    STATUS = "status"


class LoginParams:
    """Login parameter names."""

    UTF8 = "utf-8"
    PASSWORD = "password"  # noqa: S105
    REDIRECT_URL = "redirect_url"
    NAME = "name"
    AVATAR_ID = "avatar_id"
    BIRTH_DATE = "birth_date"
    PROFILE_IMAGE = "profile_image"
    LOGIN_TYPE = "login_type"
    TYPE = "type"
    REGULAR = "regular"


class EmailTemplates:
    """Email body and subject templates."""

    FRIEND_INVITE_SUBJECT = "{0} invited you to join!"
    FRIEND_INVITE_MESSAGE = (
        "Hi,\n\n{0} has invited you to join our platform.\n"
        "Click here to register: {1}\n\nThanks!"
    )


class RedirectTemplates:
    """Redirect URL templates for mobile app navigation."""

    VERIFY_OTP = "erosnowapp://verify_otp?{type}={receiver}&intent={intent}"
    SET_FORGOT_PASSWORD = "erosnowapp://set_forgot_password?{type}={receiver}&intent={intent}"  # noqa: S105


class CeleryQueues:
    """Celery queue names."""

    BLOCK_IP_QUEUE = "block_ip_queue"


class EmailSubjects:
    """Email subjects."""

    ONE_TIME_PASSWORD = "One Time Password."  # noqa: S105
    RESET_PASSWORD = "Reset Your Password - OTP"  # noqa: S105


class EmailMessages:
    """Email body messages."""

    ONE_TIME_PASSWORD = "{0} is your one time password to set up your ErosUniverse account. It is valid for 3 minutes."  # noqa: S105, E501
    RESET_PASSWORD = "{0} is your one time password to reset your ErosUniverse account password. It is valid for 3 minutes."  # noqa: S105, E501


class TemplateParams:
    """Template parameter keys."""

    OTP_CODE = "otp_code"
    USERNAME = "username"
    RESET_URL = "reset_url"
    OTP = "otp"
    VAR = "var"


class LogMessages:
    """Log messages."""

    CLIENT_IP_MISSING = "Client IP (x_forwarded_for) Missing"
    IP_BLOCKED = "IP is blocked: {0}"
    OTP_REQ_COUNT = "OTP request count for {0}_{1}: {2}"
    TOO_MANY_REQUESTS_BLOCKING = "Too many OTP requests, blocking IP: {0}_{1}"
    SMS_SEND_FAILED = "Failed to send SMS: {0}"
    SMS_SEND_EXCEPTION = "SMS Send failed: {0}"
    EMAIL_SEND_FAILED = "Failed to send OTP email via CommService: {0}"
    BREVO_TEMPLATE_NOT_CONFIGURED = "BREVO_OTP_RESEND_TEMPLATE_ID not configured"
    REDIS_ERROR_INCREMENT = "Redis error during OTP increment for {0}_{1}: {2}"


class RedisLogMessages:
    """Redis related log messages."""

    REMOVE_DEVICE_TOKEN_ERROR = (
        "Error removing device token from redis: {0}"  # noqa: S105
    )
    SAVE_DEVICE_TOKEN_ERROR = "Error saving device token to redis: {0}"  # noqa: S105
    ADD_DEVICE_TOKEN_ERROR = "Error adding device token to redis: {0}"  # noqa: S105
    SADD_ERROR = "Error in sadd: {0}"
    SREM_ERROR = "Error in srem: {0}"
    SMEMBERS_ERROR = "Error in smembers: {0}"
    LPUSH_ERROR = "Error in lpush: {0}"
    GET_LIST_ERROR = "Error in get_list: {0}"
    LREM_ERROR = "Error in lrem: {0}"
    SET_DICT_ERROR = "Error in set_dict: {0}"
    GET_VAL_ERROR = "Error in get_val: {0}"
    SET_VAL_ERROR = "Error in set_val: {0}"
    REMOVE_KEY_ERROR = "Error in remove_key: {0}"
    INCR_VAL_ERROR = "Error in incr_val: {0}"
    EXPIRE_KEY_ERROR = "Error in expire_key: {0}"


class ServiceLogMessages:
    """Service related log messages."""

    LOG_TIME = "Time for EmailDnsVerifyService"
    UNHANDLED_EXCEPTION_DOMAIN = "Unhandled exception for domain"
    UNABLE_TO_CONNECT_SMTP = "UNABLE TO CONNECT SMTP SERVER"
    DEVICE_REGISTERED = "Device registered"


class LegacyLogMessages:
    """Legacy API related log messages."""

    WOULD_BLOCK_IP = "Would block IP address {0}_{1} for 24 hours (Redis disabled)."
    LEGACY_API_CALL_FAILED = "Legacy API call failed: {0}"


class AppleLogMessages:
    """Apple OAuth related log messages."""

    FETCH_KEYS_FAILED = "Failed to fetch Apple public keys: {0}"
    ID_TOKEN_EXPIRED = "Apple ID Token expired"  # noqa: S105
    INVALID_TOKEN = "Invalid Apple Token: {0}"  # noqa: S105
    UNEXPECTED_ERROR = "Unexpected error during Apple verification: {0}"


class AuthLogMessages:
    """Authentication related log messages."""

    BCRYPT_VERIFICATION_FAILED = "Bcrypt verification failed: {0}"
    JWT_DECODE_FAILED = "JWT decode failed: {0}"


class EmailVerificationCacheKeys:
    """Cache keys for email verification."""

    DNS_INVALID_DOMAINS = "dns.invalid_domains.{0}"
    DNS_SKIP_DOMAINS = "dns.skip_domains_for_verification"
    DNS_VALID_EMAILS = "dns.valid_emails.{0}"
    DNS_INVALID_EMAILS = "dns.invalid_emails.{0}"
    DNS_VALID_DOMAINS = "dns.valid_domains.{0}"


class UserStates:
    """User states for deep linking."""

    U001 = "U001"
    U002 = "U002"


# Custom Messages
class SuccessMessages:
    """Success messages."""

    COUNTRIES_FETCHED = "Countries fetched successfully."
    COUNTRY_FETCHED = "Country fetched successfully."
    COUNTRY_LOCALES_FETCHED = "Country locales fetched successfully."
    HEALTH_CHECKUP = "Service is healthy."
    SUCCESS = "true"
    MESSAGE = "Information retrived successdully"
    DATA = "null"
    DEVICE_INVITED = "Device invited successfully"
    DEVICE_ALREADY_INVITED = "Device already invited"
    USER_CREATED_REDIRECT_OTP = "User Created. Redirect to OTP verification"
    USER_PROFILE_RETRIEVED = "User Information Retrieved"
    USER_LOGGED_IN = "User logged in successfully"
    OTP_SENT = "OTP sent successfully"
    OTP_VERIFIED = "OTP verified successfully"
    EMAIL_OR_MOBILE_REQUIRED = "Either email or mobile number is required."
    USER_NOT_FOUND = "User not found."
    ACCOUNT_LOCKED = (
        "Your account is temporarily locked due to multiple failed attempts."
    )
    PASSWORD_CHANGED_SUCCESS = "Password changed successfully."  # noqa: S105
    USER_LOGGED_OUT_SUCCESS = "User was logged out successfully."
    USER_DEACTIVATED_SUCCESS = "Your account has been successfully deactivated."
    PASSWORD_RESET_SUCCESS = "Password reset successful"  # noqa: S105
    USER_REGISTERED_VERIFIED = "User registered and verified successfully."
    WAITLIST_QUEUE_STATUS = (
        "You're #{0} in the queue, with this {1}. We'll notify you when it is ready."
    )
    WAITLIST_ALREADY_EXISTS = "Already on the Waitlist."
    WAITLIST_OTP_RESENT = "{0} already exists but not verified. OTP has been resent."
    WAITLIST_OTP_SENT = "OTP sent to your {0}. Please verify to confirm your spot."
    FRIEND_INVITES_SENT = "{0} invites sent successfully"
    EMAIL_ALREADY_VERIFIED = "This email is already verified."
    MOBILE_ALREADY_VERIFIED = "This mobile number is already verified."
    OTP_RESENT = "A new OTP has been sent."
    INVITER_NOT_REGISTERED = "Inviter must be a registered user to send invites."
    PROFILE_UPDATED = "Profile Updated"
    EMAIL_UPDATED = "User Email updated successfully."
    MOBILE_UPDATED = "User Mobile updated successfully."
    DEVICE_REGISTERED_SUCCESS = "Device registered successfully"
    TOKEN_REFRESHED_SUCCESSFULLY = "Token refreshed successfully"  # noqa: S105


class ErrorCodes:
    """Error codes."""

    GENERAL_ERROR_CODE = "US00"
    HEALTH_CHECK_FAILED_CODE = "US01"
    INTERNAL_SERVER_ERROR_CODE = "US02"
    MISSING_HEADERS_CODE = "US03"
    MISSING_HEADERS_DETAILS_CODE = "US04"
    DB_CONNECTION_ERROR_CODE = "US05"
    DB_QUERY_ERROR_CODE = "US06"
    DB_TIMEOUT_ERROR_CODE = "US07"
    DB_INTEGRITY_ERROR_CODE = "US08"
    DB_DATA_ERROR_CODE = "US09"
    DB_OPERATION_ERROR_CODE = "US10"
    DATA_VALIDATION_ERROR_CODE = "US11"
    CACHE_ERROR_CODE = "US12"
    CACHE_SERIALIZATION_ERROR_CODE = "US13"
    CACHE_OPERATION_ERROR_CODE = "US14"
    CACHE_CONNECTION_ERROR_CODE = "US15"
    COUNTRY_NOT_FOUND_CODE = "US16"
    COUNTRY_LOCALES_FETCHED_CODE = "US17"
    LANGUAGE_NOT_FOUND_CODE = "US18"
    UNAUTHORIZED_CODE = "US20"
    FORBIDDEN_CODE = "US21"
    CONFIGURATIONS_NOT_FOUND_CODE = "US22"
    COUNTRY_DATA_NOT_FOUND_CODE = "US23"
    LANGUAGES_NOT_FOUND_CODE = "US24"
    TRANSLATIONS_NOT_FOUND_CODE = "US25"
    DEVICE_NOT_INVITED = "US041"
    COUPON_ID_INVALID = "US042"
    COUPON_EXPIRED = "US043"
    EMAIL_OR_MOBILE_REQUIRED = "US004"
    CALLING_CODE_REQUIRED = "US018"
    PASSWORD_REQUIRED = "US017"  # noqa: S105
    USER_ALREADY_REGISTERED = "US001"
    COMM_SERVICE_API_CALL_FAILED = "US021"
    MOBILE_INVALID = "US022"
    FORGOT_PASSWORD = "US023"  # noqa: S105
    OTP_EXPIRED = "US024"
    OTP_TOO_MANY_ATTEMPTS = "US025"
    IP_BLOCKED = "US026"
    IP_MISSING = "US027"
    REDIS_DOWN = "US028"
    VALIDATION = "US004"
    USER_NOT_FOUND = "US002"
    BLOCKED = "US003"
    USER_TOKEN_NOT_VALID = "US031"  # noqa: S105

    # Login Specific
    USER_NOT_FOUND_LOGIN_CODE = "US002"
    INCORRECT_PASSWORD_CODE = "US021"  # noqa: S105
    UNAUTHORIZED_LOGIN_CODE = "US401"
    INVALID_INPUT_CODE = "US029"
    CLIENT_ID_VALIDATION_FAILED_CODE = "US030"
    BAD_REQUEST_CODE = "US400"
    OTP_NOT_VERIFIED_CODE = "US404"
    ACCOUNT_LOCKED_CODE = "US409"
    PROFILE_NOT_FOUND_CODE = "US403"
    VERIFICATION_REQUIRED_CODE = "US402"
    INVALID_INPUT = "US400"
    PROFILE_NOT_FOUND = "US403"
    USER_TOKEN_NOT_FOUND_CODE = "US033"  # noqa: S105
    FACEBOOK_AUTH_ERROR_CODE = "US034"
    GOOGLE_WRONG_ISSUER_CODE = "US035"
    INVALID_SOCIAL_UID_CODE = "US036"
    INVALID_SOCIAL_TOKEN_CODE = "US037"  # noqa: S105
    APPLE_KEY_FETCH_ERROR_CODE = "US038"
    DEVICE_REGISTRATION_ERROR_CODE = "US039"
    FUSION_AUTH_ERROR_CODE = "US040"
    BOOTSTRAP_KEY_ID_NOT_CONFIGURED_CODE = "US044"
    FAILED_TO_GENERATE_REFRESH_TOKEN_CODE = "US045"  # noqa: S105
    ACCOUNT_LOCKED = "US409"
    PASSWORDS_DO_NOT_MATCH = "US046"
    INVALID_OLD_PASSWORD = "US047"  # noqa: S105
    PAYLOAD_NOT_ENCRYPTED_CODE = "US048"


class ErrorMessages:
    """Error messages."""

    HEALTH_CHECK_FAILED = "Service is unavailable due to failed health check."
    INTERNAL_SERVER_ERROR = "Internal server error"
    MISSING_HEADERS = "Required headers are missing"
    MISSING_HEADERS_DETAILS = "Required headers are missing"
    DB_CONNECTION_ERROR = "Failed to connect to DB"
    DB_QUERY_ERROR = "Failed to execute DB query"
    DB_TIMEOUT_ERROR = "Database query timed out"
    DB_INTEGRITY_ERROR = "Database integrity constraint violated"
    DB_DATA_ERROR = "Invalid data for database operation"
    DB_OPERATION_ERROR = "Database operational error occurred"
    DATA_VALIDATION_ERROR = "Pydantic data validation failed"
    INVALID_TOKEN_TYPE = "Invalid token type"  # noqa: S105
    BOOTSTRAP_KEY_ID_NOT_CONFIGURED = "Bootstrap key ID not configured"
    FAILED_TO_GENERATE_REFRESH_TOKEN = (
        "Failed to generate refresh token via FusionAuth"  # noqa: S105
    )
    REFRESH_TOKEN_INVALID = "Invalid or expired refresh token"  # noqa: S105
    ACCESS_TOKEN_ISSUE_FAILED = "Failed to issue new access token"  # noqa: S105
    CACHE_ERROR = "Cache operation failed"
    CACHE_SERIALIZATION_ERROR = "Cache serialization/deserialization error"
    CACHE_OPERATION_ERROR = "Cache operational error occurred"
    CACHE_CONNECTION_ERROR = "Failed to connect to cache"
    CONFIGURATIONS_NOT_FOUND = "Requested configurations not found"
    COUNTRY_NOT_FOUND = "Requested country not found"
    COUNTRY_LOCALES_FETCHED = "Country locales fetched successfully."
    COUNTRY_DATA_NOT_FOUND = "Country data not found."
    BAD_REQUEST = "Bad request."
    UNAUTHORIZED = "Unauthorized access."
    FORBIDDEN = "Forbidden access."
    DEVICE_NOT_INVITED = "Device is Not Invited"
    DEVICE_ID_REQUIRED = "device_id is required"
    DEVICE_ALREADY_INVITED = "Device already invited"
    COUPON_ID_REQUIRED = "coupon_id is required"
    COUPON_ID_INVALID = "coupon_id is not valid"
    COUPON_EXPIRED = "Coupon expired or consumed"
    EMAIL_OR_MOBILE_REQUIRED = "Either email or mobile number is required"
    CALLING_CODE_REQUIRED = "Calling code is required when mobile number is provided"
    PASSWORD_REQUIRED = "Password is required"  # noqa: S105
    USER_ALREADY_REGISTERED = "User already registered"
    COMM_SERVICE_API_CALL_FAILED = "Not able to send or validate OTP, please try again"
    MOBILE_INVALID = "Mobile number is not valid"
    FORGOT_PASSWORD = "Forgot Password"  # noqa: S105
    OTP_EXPIRED = "OTP Expired"
    OTP_INVALID_OR_EXPIRED = "OTP is Invalid or Expired"
    OTP_TOO_MANY_ATTEMPTS = "OTP Too Many Attempts"
    IP_BLOCKED = "IP is blocked"
    PROVIDE_EMAIL_OR_MOBILE = (
        "Provide only email OR only mobile with calling_code, not both"
    )
    WAITLIST_ENTRY_NOT_FOUND = "No waitlist entry found for this {0}"
    INVITER_NOT_FOUND = "Inviter not found"
    IP_MISSING = "Client IP not provided"
    REDIS_DOWN = "Redis server is down"
    USER_NOT_FOUND = "User not found"
    PROFILE_FETCH_FAILED = "Failed to fetch user profile"
    INVALID_INPUT = "Invalid input data"
    CLIENT_ID_VALIDATION_FAILED = "Invalid Client ID"
    USER_TOKEN_NOT_VALID = "Invalid Token"  # noqa: S105
    STATE_NOT_FOUND = "State not found"
    INVITE_DB_INSERT_FAILED = "INVITE_DB_INSERT_FAILED"
    INVITE_SEND_FAILED = "INVITE_SEND_FAILED"

    # Login Specific
    INCORRECT_PASSWORD = "Incorrect password."  # noqa: S105
    USER_NOT_FOUND_LOGIN = "User not found."
    ACCOUNT_LOCKED = (
        "Your account is temporarily locked due to multiple failed login attempts."
    )
    ACCOUNT_LOCKED_DETAILS = "Please try again after some time."
    USER_TOKEN_NOT_FOUND = "Authentication token not found or invalid."  # noqa: S105
    INVALID_OLD_PASSWORD = "The old password provided is incorrect."  # noqa: S105
    PASSWORDS_DO_NOT_MATCH = "New passwords do not match."
    INCORRECT_PASSWORD_DETAILS = "The password entered is incorrect."  # noqa: S105
    USER_NOT_FOUND_DETAILS = "No user exists with the provided email or mobile."

    FACEBOOK_AUTH_ERROR = "Facebook authentication failed."
    DEVICE_REGISTERED = "Device registered successfully."
    FUSION_AUTH_VALIDATION_ERROR = "Could not validate credentials"
    FUSION_AUTH_REGISTRATION_ERROR = "Failed to register user to application"
    FUSION_AUTH_SYNC_ERROR = "Failed to sync user with Authentication Provider"
    FUSION_AUTH_TOKEN_ERROR = (
        "Authentication Provider could not issue token"  # noqa: S105
    )
    GOOGLE_WRONG_ISSUER = "Invalid Google issuer."
    INVALID_SOCIAL_UID = "Social UID mismatch."
    INVALID_SOCIAL_TOKEN = "Invalid social token."  # noqa: S105
    APPLE_KEY_FETCH_ERROR = "Failed to fetch Apple auth keys."
    INVALID_EMAIL_DOMAIN = "Invalid email domain"
    EMAIL_DOES_NOT_EXIST = "Email doesn't exist"
    EMAIL_DOMAIN_CONNECTION_ERROR = "Email domain connection error"
    DEVICE_REGISTRATION_FAILED = "Device registration failed"
    # Duplicates removed here
    DEVICE_ID_MISSING = "Device ID missing"
    TIMESTAMP_MISSING = "Timestamp missing in payload"
    REQUEST_EXPIRED = "Request expired (Timestamp check failed)"
    INSTALL_ID_MISSING = "install_id missing"
    INVALID_ENCRYPTED_DATA_LENGTH = "Invalid Encrypted Data Length"
    KEY_RETRIEVAL_FAILED = "Key Retrieval Failed"
    DECRYPTION_FAILED = "Decryption Failed"
    EMAIL_OR_MOBILE_CC_REQUIRED = (
        "Either email or mobile with calling_code must be provided."
    )
    INVITED_LIST_CANNOT_BE_EMPTY = "invited_list cannot be empty."
    PAYLOAD_DECRYPTION_FAILED = "Payload Decryption Failed"
    DEVICE_NOT_REGISTERED = "Device not registered"
    DEVICE_ALREADY_REGISTERED = "Device already registered"
    PRIVATE_KEY_NOT_FOUND = "Private Key not found on server"
    DB_ERROR = "Database Error"
    VERIFICATION_REQUIRED = "Verification required"
    OTP_NOT_VERIFIED_FOR_UPDATED_EMAIL_OR_MOBILE = (
        "OTP not verified for updated email or mobile"
    )
    USER_NOT_FOUND_BYPASS = "User not found (bypass)"
    PAYLOAD_NOT_ENCRYPTED = "Payload is not encrypted"


class Headers:
    """HTTP Headers."""

    X_API_CLIENT = "ID identifying the application (x-client-key)."
    X_DEVICE_ID = "UUID"
    X_PLATFORM = "Platform key identifier (eg. android, ios, web)."
    X_COUNTRY = "Country code (eg. IN, US, UK)."
    X_APP_VERSION = "Application version (eg. 1.0.0)"
    X_API_VERSION = "API version (eg. 1.0.0)"
    X_API_TOKEN = "API token (eg. 1.0.0)"  # noqa: S105
    X_DEVICE_TYPE = "Type of device (eg. mobile, tablet, desktop)."
    X_DEVICE_NAME = "Name of the device (eg. iPhone 13, Samsung Galaxy S21)."
    USER_AGENT = "User-Agent string from the client."


class HeaderKeys:
    """HTTP Header Keys."""

    X_API_TOKEN = "x-api-token"  # noqa: S105
    API_TOKEN = "api_token"  # noqa: S105
    X_DEVICE_ID = "x-device-id"
    DEVICE_ID = "device_id"
    X_API_CLIENT = "x-api-client"
    API_CLIENT = "api_client"
    X_FORWARDED_FOR = "x-forwarded-for"
    X_PLATFORM = "x-platform"
    X_APP_VERSION = "x-app-version"
    X_COUNTRY = "x-country"
    X_DEVICE_TYPE = "x-device-type"
    X_DEVICE_NAME = "x-device-name"
    USER_AGENT = "user-agent"
    CONTENT_TYPE = "Content-Type"
    X_LOAD_TEST_BYPASS = "x-load-test-bypass"


class Intents:
    """OTP verification intents."""

    REGISTRATION = "registration"
    FORGOT_PASSWORD = "forgot_password"  # noqa: S105
    UPDATE_EMAIL = "update_email"
    UPDATE_MOBILE = "update_mobile"
    WAITLIST = "waitlist"
    UPDATE_PROFILE = "update_profile"


class Description(str):
    """Constants for DESCRIPTION and related string values used in responses.

    This class defines string constants used across the application for consistent
    message handling and API responses.
    """

    PAGE = "Page number for paginated response."
    COUNT = "Number of records per page."
    ORDER = "Sort order."
    SORT = "Field to sort by (e.g., rank, created_at)."
    PAGE_ID = "Page ID."
    TYPE = "Filter items by type."
    APPNAME = "Application name."
    COUNTRY_CODE_DESC = "2-letter country code."
    CACHE_FLUSH_SCOPE = "Scope of cache flush it can be db or all."
    CACHE_FLUSH_DB = "Redis DB cache flushed successfully."
    CACHE_FLUSH_ALL = "All Redis DBs flushed successfully."
    LANGUAGE = "Language short code (e.g., en, hi, tl)"
    TEXT_KEY = "Text key to retrieve for translations."
    REDIS_KEY_PATTERN = "Redis key pattern to delete (e.g., 'languages:*')"
    REDIS_CACHE_KEY = "Exact Redis key to delete"
    CONFIGURATIONS_FETCHED = "Configurations fetched successfully"
    CACHE_STATS_RETRIEVED = "Cache statistics retrieved successfully"
    LANGUAGE_KEY_DESC = "Unique key identifier for the language."
    ACTIVE = "Filter by active/inactive status. value can be True/False"
    LIMIT = "Maximum number of results per page"
    CONFIG_KEY = "configurations:all"
    COUNTRY_KEY = "countries:all"
    COUNTRY_CODE = "countries:code"
    LANGUAGE_KEY = "languages:key"
    LANGUAGE_ALL = "languages:all"

    # User App Constants
    DEVICE_ID = "Unique device identifier"
    COUPON_ID = "Coupon code for invitation"
    EMAIL = "User email address"
    MOBILE = "User mobile number"
    CALLING_CODE = "International calling code"
    PASSWORD = "User password"  # noqa: S105
    NEW_PASSWORD = "New password"  # noqa: S105
    NEW_PASSWORD_CONFIRM = "New password confirmation"  # noqa: S105
    NAME = "Full name of the user"
    AVATAR_ID = "Avatar ID"
    BIRTH_DATE = "Birth date (YYYY-MM-DD)"
    PROFILE_IMAGE = "Profile image URL or base64"
    OTP = "One Time Password"
    INTENT = "Purpose of OTP verification"
    GENDER = "Gender (M/F/O)"
    ABOUT_ME = "Bio or About Me"
    NICK_NAME = "Nickname"
    COUNTRY = "Country code"
    INVITED_LIST = "List of emails or contact objects"
    SOCIAL_USER_ID = "Social User ID"
    OAUTH_TOKEN = "OAuth Token"  # noqa: S105
    PUSH_TOKEN = "Push notification token"  # noqa: S105
    DEVICE_IP = "IP address of the device"
    IS_VPN = "Whether the device is using a VPN"
    IS_ANONYMOUS_PROXY = "Whether the device is strictly an anonymous proxy"
    RESIDENCY_VERIFIED = "Whether residency matches"
    IS_ROOTED = "Whether the device is rooted"
    IS_JAILBROKEN = "Whether the device is jailbroken"
    DEVICE_ACTIVE = "Whether the device is active"
    DRM_TYPE = "Digital Rights Management type"
    HARDWARE_ENCRYPTION = "Whether hardware encryption is enabled"
    TRANSACTION_TYPE = "Type of transaction"
    IS_IP_LEGAL = "Whether IP is legal"
    NATIVE_TOKEN = "Native token"  # noqa: S105
    DATE_DEACTIVATED = "Date when the device was deactivated"


class LoggerConfigs:
    """Logger setup constants."""

    ROTATION_PERIOD = "1 day"
    RETENTION_PERIOD = "10 days"
    LOG_LEVEL_ERROR = "ERROR"
    LOG_LEVEL_DEBUG = "DEBUG"


class AuthConfig:
    """Authorization constants."""

    ALGORITHM = "HS256"
    RS256 = "RS256"
    DECODE_CODE = "utf-8"


class JwtOptions:
    """JWT verification options."""

    VERIFY_EXP = "verify_exp"


Messages = SuccessMessages

Intent = Intents
