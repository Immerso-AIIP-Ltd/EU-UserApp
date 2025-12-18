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
    COUNTRIES_ALL = "countries:all:{language}:{page}:{limit}:{active}:{api_version}"
    COUNTRY_BY_CODE = "countries:code:{country_code}:{language}:{appname}:{api_version}"
    COUNTRY_LANGUAGES = "countries:lang:{country_code}:{language}:{appname}:{page}:{limit}:{api_version}"  # noqa: E501
    LANGUAGES_ALL = (
        "languages:all:{language}:{appname}:{page}:{limit}:{active}:{api_version}"
    )
    LANGUAGE_BY_KEY = "languages:key:{language}:{appname}:{api_version}"
    TRANSLATIONS_BY_LANG = (
        "translations:lang:{language}:{appname}:{page}:{limit}:{api_version}"
    )
    TRANSLATIONS_BY_KEY = "translations:key:{text_key}:{appname}:{api_version}"


class CacheTTL:
    """Cache Time-To-Live (TTL) values in seconds."""

    TTL_FAST = 900  # 15 minutes
    TTL_STANDARD = 3600  # 1 hour
    TTL_EXTENDED = 43200  # 12 hours
    TTL_MAX = 86400  # 24 hours


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
    TRANSLATION_LANGUAGE = "Translations retrieved successfully."
    TRANSLATION_TEXTKEY = "Text translations retrieved successfully."
    LANGUAGES_RETRIEVED = "Languages retrieved successfully."
    LANGUAGE_RETRIEVED = "Language retrieved successfully."
    HEALTH_CHECKUP = "Service is healthy."


class ErrorCodes:
    """Error codes."""

    GENERAL_ERROR_CODE = "EU00"
    HEALTH_CHECK_FAILED_CODE = "EU01"
    INTERNAL_SERVER_ERROR_CODE = "EU02"
    MISSING_HEADERS_CODE = "EU03"
    MISSING_HEADERS_DETAILS_CODE = "EU04"
    DB_CONNECTION_ERROR_CODE = "EU05"
    DB_QUERY_ERROR_CODE = "EU06"
    DB_TIMEOUT_ERROR_CODE = "EU07"
    DB_INTEGRITY_ERROR_CODE = "EU08"
    DB_DATA_ERROR_CODE = "EU09"
    DB_OPERATION_ERROR_CODE = "EU10"
    DATA_VALIDATION_ERROR_CODE = "EU11"
    CACHE_ERROR_CODE = "EU12"
    CACHE_SERIALIZATION_ERROR_CODE = "EU13"
    CACHE_OPERATION_ERROR_CODE = "EU14"
    CACHE_CONNECTION_ERROR_CODE = "EU15"
    COUNTRY_NOT_FOUND_CODE = "EU16"
    COUNTRY_LOCALES_FETCHED_CODE = "EU17"
    LANGUAGE_NOT_FOUND_CODE = "EU18"
    BAD_REQUEST_CODE = "EU19"
    UNAUTHORIZED_CODE = "EU20"
    FORBIDDEN_CODE = "EU21"
    CONFIGURATIONS_NOT_FOUND_CODE = "EU22"
    COUNTRY_DATA_NOT_FOUND_CODE = "EU23"
    LANGUAGES_NOT_FOUND_CODE = "EU24"
    TRANSLATIONS_NOT_FOUND_CODE = "EU25"


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
    LANGUAGE_NOT_FOUND = "Language not found."
    LANGUAGES_NOT_FOUND = "Languages not found."
    TRANSLATIONS_NOT_FOUND = "Translations not found."
    BAD_REQUEST = "Bad request."
    UNAUTHORIZED = "Unauthorized access."
    FORBIDDEN = "Forbidden access."


class Headers:
    """HTTP Headers."""

    X_PLATFORM = "x-platform"
    X_VERSION = "x-version"
    X_APPNAME = "x-appname"
    X_REQUEST_ID = "x-request-id"
    X_USER_ID = "x-user-id"


class Description(str):
    """Constants for DESCRIPTION and related string values used in responses.

    This class defines string constants used across the application for consistent
    message handling and API responses.
    """

    PLATFORM = "Platform key identifier."
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
    TRANSLATIONS_LANGUAGE = "translations:lang"
    TRANSLATIONS_KEY = "translations:textkey"

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
