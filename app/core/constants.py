"""Application constants."""


# General
class AppConfig:
    """Application configuration."""

    NAME = "EU-Config"
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
    CACHE_KEY_USER_PROFILE = "user_profile:{user_id}:platform:{platform}:version:{version}:country:{country}"


class CacheTTL:
    """Cache Time-To-Live (TTL) values in seconds."""

    TTL_FAST = 900  # 15 minutes
    TTL_STANDARD = 3600  # 1 hour
    TTL_EXTENDED = 43200  # 12 hours
    TTL_MAX = 86400  # 24 hours
    TTL_INVITE_DEVICE = 60
    TTL_USER_PROFILE = 3600 


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


class ResponseParams:
    """Response field names."""

    # Top-level response fields
    SUCCESS = "success"
    MESSAGE = "message"
    DATA = "data"
    META = "meta"
    ERROR = "error"

    # Meta fields
    API_VERSION = "api_version"
    TIMESTAMP = "timestamp"
    REQUEST_ID = "request_id"
    TOTAL_RECORDS = "total_records"
    PAGE = "page"
    PER_PAGE = "per_page"
    TOTAL_PAGES = "total_pages"

    # Error fields (if needed)
    ERROR_CODE = "error_code"
    ERROR_DETAILS = "error_details"


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
    DEVICE_INVITED = "Device is already invited"
    USER_CREATED_REDIRECT_OTP = "User Created. Redirect to OTP verification"
    USER_PROFILE_RETRIEVED = "User Information Retrieved"


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
    BAD_REQUEST_CODE = "US19"
    UNAUTHORIZED_CODE = "US20"
    FORBIDDEN_CODE = "US21"
    CONFIGURATIONS_NOT_FOUND_CODE = "US22"
    COUNTRY_DATA_NOT_FOUND_CODE = "US23"
    LANGUAGES_NOT_FOUND_CODE = "US24"
    TRANSLATIONS_NOT_FOUND_CODE = "US25"
    DEVICE_NOT_INVITED = "US100"
    COUPON_ID_INVALID = "US400"
    COUPON_EXPIRED = "US200"
    EMAIL_OR_MOBILE_REQUIRED = "US004"
    CALLING_CODE_REQUIRED = "US018"
    PASSWORD_REQUIRED = "US017"
    USER_ALREADY_REGISTERED = "US001"
    COMM_SERVICE_API_CALL_FAILED = "US021"
    MOBILE_INVALID = "US022"
    FORGOT_PASSWORD = "US023"
    OTP_EXPIRED = "US024"
    OTP_TOO_MANY_ATTEMPTS = "US025"
    IP_BLOCKED = "US026"
    IP_MISSING = "US027"
    REDIS_DOWN = "US028"


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
    PASSWORD_REQUIRED = "Password is required"
    USER_ALREADY_REGISTERED = "User already registered"
    COMM_SERVICE_API_CALL_FAILED = "Not able to send or validate OTP, please try again"
    MOBILE_INVALID = "Mobile number is not valid"
    FORGOT_PASSWORD = "Forgot Password"
    OTP_EXPIRED = "OTP Expired"
    OTP_TOO_MANY_ATTEMPTS = "OTP Too Many Attempts"
    IP_BLOCKED = "IP is blocked"
    IP_MISSING = "Client IP not provided"
    REDIS_DOWN = "Redis server is down"
    USER_NOT_FOUND = "User not found"
    PROFILE_FETCH_FAILED = "Failed to fetch user profile"


class Headers:
    """HTTP Headers."""

    X_API_CLIENT = "ID identifying the application (x-client-key)."
    X_DEVICE_ID = "UUID"
    X_PLATFORM = "Platform key identifier (eg. android, ios, web)."
    X_COUNTRY = "Country code (eg. IN, US, UK)."
    X_APP_VERSION = "Application version (eg. 1.0.0)"
    X_API_TOKEN = "API token (x-api-token)."

class Intent:
    REGISTRATION = "registration"
    FORGOT_PASSWORD = "forgot_password"
    UPDATE_EMAIL = "update_email"
    UPDATE_MOBILE = "update_mobile"


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
    PASSWORD = "User password"
    NEW_PASSWORD = "New password"
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
    OAUTH_TOKEN = "OAuth Token"


class LoggerConfigs:
    """Logger setup constants."""

    ROTATION_PERIOD = "1 day"
    RETENTION_PERIOD = "10 days"
    LOG_LEVEL_ERROR = "ERROR"
    LOG_LEVEL_DEBUG = "DEBUG"

class AuthConfig:
    "Authorization constants"
    
    ALGORITHM = "HS256"
    DECODE_CODE = "utf-8"