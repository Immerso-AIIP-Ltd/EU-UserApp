
import logging
from typing import Any, Dict

from app.api.v1.service.register_commservice import call_communication_api
from app.core.constants import (
    HeaderKeys,
    HeaderValues,
    HTTPMethods,
    LogMessages,
)
from app.settings import settings

logger = logging.getLogger(__name__)

class AssetManagerService:
    """Service to interact with the Asset Manager API."""

    COMMIT_ENDPOINT = settings.asset_commit_url

    @staticmethod
    async def commit_asset(
        temp_key: str,
        user_id: str,
        headers: Dict[str, Any],
    ) -> Dict[str, Any] | None:
        """
        Call the commit API to move/confirm the asset.

        Args:
            temp_key: The temporary key of the asset.
            user_id: The ID of the user.
            headers: Headers to pass to the API (extracted from original request).

        Returns:
            The 'data' dictionary from the response if successful, else None.
        """
        payload = {
            "temp_key": temp_key,
            "intent": "PROFILE",
            "user_id": str(user_id),
        }

        # Construct headers for the request.
        req_headers = {
            HeaderKeys.CONTENT_TYPE: HeaderValues.APPLICATION_JSON,
            "accept": HeaderValues.APPLICATION_JSON,
            HeaderKeys.X_API_CLIENT: "android",
            HeaderKeys.X_DEVICE_ID: "device-123",
            HeaderKeys.X_PLATFORM: "mobile",
            HeaderKeys.X_COUNTRY: "US",
            HeaderKeys.X_APP_VERSION: "1.0.0",
        }

        # Override with actual headers if present
        header_map = {
            HeaderKeys.X_API_CLIENT: "api_client",
            HeaderKeys.X_DEVICE_ID: "device_id",
            HeaderKeys.X_PLATFORM: "platform",
            HeaderKeys.X_COUNTRY: "country",
            HeaderKeys.X_APP_VERSION: "app_version",
        }

        for header_key, internal_key in header_map.items():
             val = headers.get(header_key) or headers.get(internal_key)
             if val:
                 req_headers[header_key] = str(val)

        try:
            response = await call_communication_api(
                url=AssetManagerService.COMMIT_ENDPOINT,
                payload=payload,
                method=HTTPMethods.POST,
                headers=req_headers,
            )

            if response and response.get("success"):
                return response.get("data")

            logger.error(LogMessages.ASSET_COMMIT_FAILED.format(response))
            return None

        except Exception as e:
            logger.error(LogMessages.ASSET_COMMIT_EXCEPTION.format(e))
            return None
