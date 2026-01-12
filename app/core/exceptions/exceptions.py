"""Custom exceptions for the application."""

from typing import Optional

from fastapi.responses import JSONResponse
from starlette import status

from app.core.constants import ErrorCodes, ErrorMessages


class AppExceptionError(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        error_type: str,
        detail: str,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.error_type = error_type
        self.detail = detail
        super().__init__(self.detail)


class AppError(Exception):
    """Base application exception."""

    http_code: int = status.HTTP_400_BAD_REQUEST
    message: str = ErrorMessages.INTERNAL_SERVER_ERROR
    error_code: str = ErrorCodes.GENERAL_ERROR_CODE

    def __init__(
        self,
        detail: Optional[str] = None,
        http_code: Optional[int] = None,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> None:
        if http_code is not None:
            self.http_code = http_code
        if message is not None:
            self.message = message
        if error_code is not None:
            self.error_code = error_code
        self.detail = detail or self.message
        super().__init__(self.detail)

    def to_response(self) -> JSONResponse:
        """Convert the error to a FastAPI JSONResponse.

        Returns:
            JSONResponse: A formatted error response with status code and error details.
        """
        return JSONResponse(
            status_code=self.http_code,
            content={
                "success": False,
                "data": {},
                "meta": {},
                "error": {
                    "code": self.http_code,
                    "error_code": self.error_code,
                    "message": self.detail,
                    "type": self.__class__.__name__,
                },
            },
        )


# Cache Exceptions
class CacheError(AppError):
    """Base exception for cache-related errors."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.CACHE_CONNECTION_ERROR
    error_code = ErrorCodes.CACHE_CONNECTION_ERROR_CODE


class CacheOperationError(CacheError):
    """Raised when cache read/write operation fails."""

    message = ErrorMessages.CACHE_OPERATION_ERROR
    error_code = ErrorCodes.CACHE_OPERATION_ERROR_CODE


class CacheConnectionError(CacheError):
    """Raised when connection to cache fails."""

    message = ErrorMessages.CACHE_CONNECTION_ERROR
    error_code = ErrorCodes.CACHE_CONNECTION_ERROR_CODE


# Database Exceptions
class DatabaseError(AppError):
    """Base exception for all database-related errors."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.DB_CONNECTION_ERROR
    error_code = ErrorCodes.DB_CONNECTION_ERROR_CODE


class DBConnectionError(DatabaseError):
    """Raised when connection to database fails."""

    message = ErrorMessages.DB_CONNECTION_ERROR
    error_code = ErrorCodes.DB_CONNECTION_ERROR_CODE


class DBQueryExecutionError(DatabaseError):
    """Raised when query execution fails."""

    message = ErrorMessages.DB_QUERY_ERROR
    error_code = ErrorCodes.DB_QUERY_ERROR_CODE


class DBTimeoutError(DatabaseError):
    """Raised when query exceeds timeout limit."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.DB_TIMEOUT_ERROR
    error_code = ErrorCodes.DB_TIMEOUT_ERROR_CODE


class DBIntegrityError(DatabaseError):
    """Raised when database integrity constraint is violated."""

    http_code = status.HTTP_409_CONFLICT
    message = ErrorMessages.DB_INTEGRITY_ERROR
    error_code = ErrorCodes.DB_INTEGRITY_ERROR_CODE


class DBDataError(DatabaseError):
    """Raised when data-related error occurs (invalid type, value, etc)."""

    http_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = ErrorMessages.DB_DATA_ERROR
    error_code = ErrorCodes.DB_DATA_ERROR_CODE


class DBOperationalError(DatabaseError):
    """Raised for database operational errors (disconnection, memory, etc)."""

    message = ErrorMessages.DB_OPERATION_ERROR
    error_code = ErrorCodes.DB_OPERATION_ERROR_CODE


class ValidationError(AppError):
    """Raised when data validation fails."""

    http_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = ErrorMessages.DATA_VALIDATION_ERROR
    error_code = ErrorCodes.DATA_VALIDATION_ERROR_CODE


class HealthCheckError(AppError):
    """Raised when health check fails."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.HEALTH_CHECK_FAILED
    error_code = ErrorCodes.HEALTH_CHECK_FAILED_CODE


class BadRequestError(AppError):
    """Raised for invalid request parameters."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.BAD_REQUEST
    error_code = ErrorCodes.BAD_REQUEST_CODE


class MissingHeadersError(BadRequestError):
    """Raised when required headers are missing."""

    message = ErrorMessages.MISSING_HEADERS
    error_code = ErrorCodes.MISSING_HEADERS_CODE


class UnauthorizedError(AppError):
    """Raised when authentication fails."""

    http_code = status.HTTP_401_UNAUTHORIZED
    message = ErrorMessages.UNAUTHORIZED
    error_code = ErrorCodes.UNAUTHORIZED_CODE


class ForbiddenError(AppError):
    """Raised when the user does not have access rights."""

    http_code = status.HTTP_403_FORBIDDEN
    message = ErrorMessages.FORBIDDEN
    error_code = ErrorCodes.FORBIDDEN_CODE


class DeviceNotInvitedError(AppError):
    """Device ID not invited."""

    http_code = status.HTTP_200_OK
    message = ErrorMessages.DEVICE_NOT_INVITED
    error_code = ErrorCodes.DEVICE_NOT_INVITED


class InvalidCouponError(AppError):
    """Coupon ID not valid."""

    http_code = status.HTTP_200_OK
    message = ErrorMessages.COUPON_ID_INVALID
    error_code = ErrorCodes.COUPON_ID_INVALID


class CouponExpiredError(AppError):
    """Coupon ID not valid."""

    http_code = status.HTTP_200_OK
    message = ErrorMessages.COUPON_EXPIRED
    error_code = ErrorCodes.COUPON_EXPIRED


class EmailMobileRequiredError(AppError):
    """Email or Mobile required."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.EMAIL_OR_MOBILE_REQUIRED
    error_code = ErrorCodes.EMAIL_OR_MOBILE_REQUIRED


class CallingCodeRequiredError(AppError):
    """Calling code required."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.CALLING_CODE_REQUIRED
    error_code = ErrorCodes.CALLING_CODE_REQUIRED


class PasswordRequiredError(AppError):
    """Password Required."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.PASSWORD_REQUIRED
    error_code = ErrorCodes.PASSWORD_REQUIRED


class UserExistsError(AppError):
    """User already exists."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.USER_ALREADY_REGISTERED
    error_code = ErrorCodes.USER_ALREADY_REGISTERED


class CommServiceAPICallFailedError(AppError):
    """Communication service API call failed."""

    http_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = ErrorMessages.COMM_SERVICE_API_CALL_FAILED
    error_code = ErrorCodes.COMM_SERVICE_API_CALL_FAILED


class RedisServerDownError(AppError):
    """Redis server down."""

    http_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = ErrorMessages.REDIS_DOWN
    error_code = ErrorCodes.REDIS_DOWN


class ClientIpNotProvidedError(AppError):
    """Client IP not provided."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.IP_MISSING
    error_code = ErrorCodes.IP_MISSING


class IpBlockedError(AppError):
    """IP address blocked."""

    http_code = status.HTTP_403_FORBIDDEN
    message = ErrorMessages.IP_BLOCKED
    error_code = ErrorCodes.IP_BLOCKED


class OtpExpiredError(AppError):
    """OTP has expired."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.OTP_EXPIRED
    error_code = ErrorCodes.OTP_EXPIRED


class OtpTooManyAttemptsError(AppError):
    """Too many OTP verification attempts."""

    http_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = ErrorMessages.OTP_TOO_MANY_ATTEMPTS
    error_code = ErrorCodes.OTP_TOO_MANY_ATTEMPTS


class MobileInvalidError(AppError):
    """Invalid mobile number."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.MOBILE_INVALID
    error_code = ErrorCodes.MOBILE_INVALID


class ForgotPasswordError(AppError):
    """Forgot password error."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.FORGOT_PASSWORD
    error_code = ErrorCodes.FORGOT_PASSWORD


# Add to existing exceptions file


class UserNotFoundError(AppError):
    """Raised when user profile is not found."""

    def __init__(self, message: str = ErrorMessages.USER_NOT_FOUND) -> None:
        super().__init__(
            http_code=status.HTTP_404_NOT_FOUND,
            message=message,
            error_code=ErrorCodes.US404,
        )


class ProfileFetchError(AppError):
    """Raised when profile fetch fails."""

    def __init__(self, detail: str = ErrorMessages.PROFILE_FETCH_FAILED) -> None:
        super().__init__(
            http_code=status.HTTP_403_FORBIDDEN,
            message=detail,
            error_code=ErrorCodes.US403,
        )


class ClientIdValidationFailedError(AppError):
    """Raised when client ID validation fails."""

    http_code = status.HTTP_401_UNAUTHORIZED
    message = ErrorMessages.CLIENT_ID_VALIDATION_FAILED
    error_code = ErrorCodes.CLIENT_ID_VALIDATION_FAILED_CODE


class InvalidInputError(AppError):
    """Raised when input data is invalid."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            http_code=status.HTTP_400_BAD_REQUEST,
            message=detail,
            error_code=ErrorCodes.US400,
        )


# UserNotFound class removed as it was merged into UserNotFoundError above.


class AccountBlockedError(AppError):
    """Raised when a user account is blocked."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_409_CONFLICT,
            message=ErrorMessages.ACCOUNT_LOCKED,
            error_code=ErrorCodes.US409,
        )


class PasswordsDoNotMatchError(AppError):
    """Raised when password and confirmation do not match."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_400_BAD_REQUEST,
            message=ErrorMessages.PASSWORDS_DO_NOT_MATCH,
            error_code=ErrorCodes.US400,
        )


class InvalidOldPasswordError(AppError):
    """Raised when the provided old password is incorrect."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_400_BAD_REQUEST,
            message=ErrorMessages.INVALID_OLD_PASSWORD,
            error_code=ErrorCodes.US400,
        )


class UserTokenNotFoundError(AppError):
    """Raised when a user token is not found."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_401_UNAUTHORIZED,
            message=ErrorMessages.USER_TOKEN_NOT_FOUND,
            error_code=ErrorCodes.USER_TOKEN_NOT_FOUND_CODE,
        )


class GoogleWrongIssuerError(AppError):
    """Raised when Google ID token has an incorrect issuer."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_401_UNAUTHORIZED,
            message=ErrorMessages.GOOGLE_WRONG_ISSUER,
            error_code=ErrorCodes.GOOGLE_WRONG_ISSUER_CODE,
        )


class InvalidSocialUIDError(AppError):
    """Raised when a social user ID is invalid."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_401_UNAUTHORIZED,
            message=ErrorMessages.INVALID_SOCIAL_UID,
            error_code=ErrorCodes.INVALID_SOCIAL_UID_CODE,
        )


class InvalidSocialTokenError(AppError):
    """Raised when a social authentication token is invalid."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_401_UNAUTHORIZED,
            message=ErrorMessages.INVALID_SOCIAL_TOKEN,
            error_code=ErrorCodes.INVALID_SOCIAL_TOKEN_CODE,
        )


class OtpInvalidError(AppError):
    """Raised when the provided OTP is invalid."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid OTP",
            error_code="US400",
        )


class RegistrationSessionClosedError(AppError):
    """Raised when the registration session has expired or been closed."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_400_BAD_REQUEST,
            message="Registration session closed or expired",
            error_code="US400",
        )


class AppleKeyFetchError(AppError):
    """Raised when fetching Apple public keys fails."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_400_BAD_REQUEST,
            message=ErrorMessages.APPLE_KEY_FETCH_ERROR,
            error_code=ErrorCodes.APPLE_KEY_FETCH_ERROR_CODE,
        )


class FacebookAuthError(AppError):
    """Raised when Facebook authentication fails."""

    def __init__(self) -> None:
        super().__init__(
            http_code=status.HTTP_401_UNAUTHORIZED,
            message=ErrorMessages.FACEBOOK_AUTH_ERROR,
            error_code=ErrorCodes.FACEBOOK_AUTH_ERROR_CODE,
        )


class DeviceAlreadyRegisteredError(AppError):
    """Raised when a device is already registered to a user."""

    def __init__(self, detail: str = "Device already registered") -> None:
        super().__init__(
            http_code=status.HTTP_409_CONFLICT,
            message=detail,
            error_code="US409",
        )


class DeviceNotRegisteredError(AppError):
    """Raised when a device is not found in the registry."""

    def __init__(self, detail: str = "Device not registered") -> None:
        super().__init__(
            http_code=status.HTTP_404_NOT_FOUND,
            message=detail,
            error_code="US404",
        )


class InvalidServiceTokenError(AppError):
    """Raised when the service token is invalid."""

    def __init__(self, message: str = ErrorMessages.USER_TOKEN_NOT_VALID) -> None:
        super().__init__(
            http_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            error_code=ErrorCodes.USER_TOKEN_NOT_VALID,
        )


class InvalidCredentialsError(AppError):
    """Invalid credentials provided."""

    def __init__(self, message: str = "Invalid credentials.") -> None:
        self.http_code = status.HTTP_401_UNAUTHORIZED
        self.code = ErrorCodes.UNAUTHORIZED_CODE
        self.message = message
        super().__init__(message=message)


class DeviceRegistrationError(AppError):
    """Raised when device registration fails."""

    def __init__(self, detail: str = "Device registration failed") -> None:
        super().__init__(
            http_code=status.HTTP_400_BAD_REQUEST,
            message=detail,
            error_code=ErrorCodes.DEVICE_REGISTRATION_ERROR_CODE,
        )


class FusionAuthError(AppError):
    """Base exception for FusionAuth related errors."""

    def __init__(
        self,
        detail: str = "FusionAuth operation failed",
        http_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(
            http_code=http_code,
            message=detail,
            error_code=ErrorCodes.FUSION_AUTH_ERROR_CODE,
        )


class OtpNotVerifiedError(AppError):
    """Exception for unverified OTP during profile update."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = "OTP not verified for updated email or mobile"
    error_code = ErrorCodes.US404


class VerificationRequiredError(AppError):
    """Exception when verification is required."""

    http_code = status.HTTP_402_PAYMENT_REQUIRED  # User requested US402
    message = "Verification required"
    error_code = ErrorCodes.US402


class BootstrapKeyIdNotConfiguredError(AppError):
    """Exception when bootstrap key ID is not configured."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = ErrorMessages.BOOTSTRAP_KEY_ID_NOT_CONFIGURED
    error_code = ErrorCodes.BOOTSTRAP_KEY_ID_NOT_CONFIGURED_CODE


class FailedToGenerateRefreshTokenError(AppError):
    """Exception when failed to generate refresh token via FusionAuth."""

    http_code = status.HTTP_400_BAD_REQUEST
    message = "Failed to generate refresh token via FusionAuth"
    error_code = ErrorCodes.FAILED_TO_GENERATE_REFRESH_TOKEN_CODE
