from typing import Any, Optional

import requests
from loguru import logger

from app.core.exceptions import FacebookAuthError, InvalidSocialUID


class FacebookOAuthService:
    """Service to handle Facebook OAuth verification."""

    NAME = "facebook"
    GRAPH_API_URL = "https://graph.facebook.com/me"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.uid: Optional[str] = None
        self.email: Optional[str] = None
        self.name: Optional[str] = None

    async def verify_access_token(self, uid: str) -> Any:
        """
        Verify the Facebook Access Token and match UID.
        """
        try:
            params = {"access_token": self.access_token, "fields": "id,name,email"}
            response = requests.get(self.GRAPH_API_URL, params=params)

            if response.status_code != 200:
                logger.error(f"Facebook Graph API Error: {response.text}")
                raise FacebookAuthError()

            data = response.json()

            if data.get("id") != uid:
                raise InvalidSocialUID()

            self.uid = data.get("id")
            self.name = data.get("name")
            self.email = data.get("email")

        except FacebookAuthError:
            raise
        except InvalidSocialUID:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during Facebook verification: {e}")
            raise FacebookAuthError()

    async def get_email(self) -> Any:
        return self.email

    async def get_name(self) -> Any:
        return self.name

    async def get_uid(self) -> Any:
        return self.uid

    async def get_token(self) -> Any:
        return self.access_token
