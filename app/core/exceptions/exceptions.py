"""Custom exceptions for the application."""

from fastapi.responses import JSONResponse
from starlette import status

from app.core.constants import ErrorCodes, ErrorMessages


class AppError(Exception):
    """Base application exception."""

    http_code: int = status.HTTP_400_BAD_REQUEST
    message: str = ErrorMessages.INTERNAL_SERVER_ERROR
    error_code: str = ErrorCodes.GENERAL_ERROR_CODE

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.message

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


