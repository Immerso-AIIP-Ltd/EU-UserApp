from typing import Optional

from fastapi import Header
from pydantic import BaseModel, Field

from app.core.constants import ErrorMessages, Headers
from app.core.exceptions.exceptions import MissingHeadersError


class CommonHeaders(BaseModel):
    """Pydantic model for common request headers."""

    platform: str = Field(..., alias="x-platform")
    version: str = Field(..., alias="x-version")
    appname: str = Field(..., alias="x-appname")
    request_id: Optional[str] = Field(None, alias="x-request-id")
    user_id: Optional[str] = Field(None, alias="x-user-id")


def validate_common_headers(
    x_platform: str = Header(..., description=Headers.X_PLATFORM),
    x_version: str = Header(..., description=Headers.X_VERSION),
    x_appname: str = Header(..., description=Headers.X_APPNAME),
    x_request_id: Optional[str] = Header(None, description=Headers.X_REQUEST_ID),
    x_user_id: Optional[str] = Header(None, description=Headers.X_USER_ID),
) -> CommonHeaders:
    """__summary__.

    Validate and return common headers required for API requests.
    This function acts as a FastAPI dependency.

    Raises:
        MissingHeadersError: If any of the required headers are missing or empty.

    Returns:
        CommonHeaders: A Pydantic model containing the validated headers.
    """
    # Strip whitespace from required headers
    x_platform = x_platform.strip()
    x_version = x_version.strip()
    x_appname = x_appname.strip()

    # Validate after stripping
    if not x_platform or not x_version or not x_appname:
        raise MissingHeadersError(detail=ErrorMessages.MISSING_HEADERS_DETAILS)

    return CommonHeaders.model_validate(
        {
            "x-platform": x_platform,
            "x-version": x_version,
            "x-appname": x_appname,
            "x-request-id": x_request_id.strip() if x_request_id else None,
            "x-user-id": x_user_id.strip() if x_user_id else None,
        },
    )
