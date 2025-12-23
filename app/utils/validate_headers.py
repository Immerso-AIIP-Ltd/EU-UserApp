from typing import Optional
from fastapi import Header
from pydantic import BaseModel, Field
from app.core.constants import ErrorMessages, Headers
from app.core.exceptions.exceptions import MissingHeadersError


class CommonHeaders(BaseModel):
    """Pydantic model for common request headers."""
    api_client: str = Field(..., alias="x-api-client")
    device_id: str = Field(..., alias="x-device-id")
    platform: str = Field(..., alias="x-platform")
    country: str = Field(..., alias="x-country")
    app_version: str = Field(..., alias="x-app-version")
    api_token: Optional[str] = Field(None, alias="x-api-token")  # Made optional


def validate_common_headers(
    x_api_client: str = Header(..., description=Headers.X_API_CLIENT),
    x_device_id: str = Header(..., description=Headers.X_DEVICE_ID),
    x_platform: str = Header(..., description=Headers.X_PLATFORM),
    x_country: str = Header(..., description=Headers.X_COUNTRY),
    x_app_version: str = Header(..., description=Headers.X_APP_VERSION),
    x_api_token: str = Header(..., description=Headers.X_API_TOKEN),
) -> dict:
    """Validate and return common headers required for API requests (including auth token).
    
    This function acts as a FastAPI dependency.
    
    Raises:
        MissingHeadersError: If any of the required headers are missing or empty.
    
    Returns:
        dict: A dictionary containing the validated headers.
    """
    # Strip required headers
    x_api_client = x_api_client.strip() if x_api_client else ""
    x_device_id = x_device_id.strip() if x_device_id else ""
    x_country = x_country.strip() if x_country else ""
    x_app_version = x_app_version.strip() if x_app_version else ""
    x_platform = x_platform.strip() if x_platform else ""
    x_api_token = x_api_token.strip() if x_api_token else ""

    if not all([x_api_client, x_device_id, x_platform, x_country, x_app_version, x_api_token]):
        raise MissingHeadersError(detail=ErrorMessages.MISSING_HEADERS_DETAILS)

    return CommonHeaders.model_validate(
        {
            "x-api-client": x_api_client,
            "x-device-id": x_device_id,
            "x-platform": x_platform,
            "x-country": x_country,
            "x-app-version": x_app_version,
            "x-api-token": x_api_token,
        },
    ).model_dump()


def validate_headers_without_auth(
    x_api_client: str = Header(..., description=Headers.X_API_CLIENT),
    x_device_id: str = Header(..., description=Headers.X_DEVICE_ID),
    x_platform: str = Header(..., description=Headers.X_PLATFORM),
    x_country: str = Header(..., description=Headers.X_COUNTRY),
    x_app_version: str = Header(..., description=Headers.X_APP_VERSION),
) -> dict:
    """Validate and return common headers WITHOUT auth token (for login/signup endpoints).
    
    This function acts as a FastAPI dependency.
    
    Raises:
        MissingHeadersError: If any of the required headers are missing or empty.
    
    Returns:
        dict: A dictionary containing the validated headers.
    """
    # Strip required headers
    x_api_client = x_api_client.strip() if x_api_client else ""
    x_device_id = x_device_id.strip() if x_device_id else ""
    x_country = x_country.strip() if x_country else ""
    x_app_version = x_app_version.strip() if x_app_version else ""
    x_platform = x_platform.strip() if x_platform else ""

    if not all([x_api_client, x_device_id, x_platform, x_country, x_app_version]):
        raise MissingHeadersError(detail=ErrorMessages.MISSING_HEADERS_DETAILS)

    return CommonHeaders.model_validate(
        {
            "x-api-client": x_api_client,
            "x-device-id": x_device_id,
            "x-platform": x_platform,
            "x-country": x_country,
            "x-app-version": x_app_version,
            "x-api-token": None,  # Not required for login
        },
    ).model_dump()