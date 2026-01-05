from typing import Any, Dict
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
    api_token: str = Field(..., alias="x-api-token")


class CommonHeadersWithoutAuth(BaseModel):
    api_client: str = Field(..., alias="x-api-client")
    device_id: str = Field(..., alias="x-device-id")
    platform: str = Field(..., alias="x-platform")
    country: str = Field(..., alias="x-country")
    app_version: str = Field(..., alias="x-app-version")


async def validate_common_headers(
    x_api_client: str = Header(..., description=Headers.X_API_CLIENT),
    x_device_id: str = Header(..., description=Headers.X_DEVICE_ID),
    x_platform: str = Header(..., description=Headers.X_PLATFORM),
    x_country: str = Header(..., description=Headers.X_COUNTRY),
    x_app_version: str = Header(..., description=Headers.X_APP_VERSION),
    x_api_token: str = Header(..., description=Headers.X_API_TOKEN),
) -> Dict[str, Any]:
    """__summary__.

    Validate and return common headers required for API requests.
    This function acts as a FastAPI dependency.

    Raises:
        MissingHeadersError: If any of the required headers are missing or empty.

    Returns:
        dict: A dictionary containing the validated headers.
    """
    # Strip required headers
    x_api_client = x_api_client.strip()
    x_device_id = x_device_id.strip()
    x_country = x_country.strip()
    x_app_version = x_app_version.strip()
    x_platform = x_platform.strip()
    x_api_token = x_api_token.strip()

    if not all(
        [x_api_client, x_device_id, x_platform, x_country, x_app_version, x_api_token]
    ):
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


async def validate_headers_without_auth(
    x_api_client: str = Header(..., description=Headers.X_API_CLIENT),
    x_device_id: str = Header(..., description=Headers.X_DEVICE_ID),
    x_platform: str = Header(..., description=Headers.X_PLATFORM),
    x_country: str = Header(..., description=Headers.X_COUNTRY),
    x_app_version: str = Header(..., description=Headers.X_APP_VERSION),
) -> Dict[str, Any]:
    """__summary__.

    Validate and return common headers required for API requests.
    This function acts as a FastAPI dependency.

    Raises:
        MissingHeadersError: If any of the required headers are missing or empty.

    Returns:
        dict: A dictionary containing the validated headers.
    """
    # Strip required headers
    x_api_client = x_api_client.strip()
    x_device_id = x_device_id.strip()
    x_country = x_country.strip()
    x_app_version = x_app_version.strip()
    x_platform = x_platform.strip()

    if not all([x_api_client, x_device_id, x_platform, x_country, x_app_version]):
        raise MissingHeadersError(detail=ErrorMessages.MISSING_HEADERS_DETAILS)

    return CommonHeadersWithoutAuth.model_validate(
        {
            "x-api-client": x_api_client,
            "x-device-id": x_device_id,
            "x-platform": x_platform,
            "x-country": x_country,
            "x-app-version": x_app_version,
        },
    ).model_dump()
