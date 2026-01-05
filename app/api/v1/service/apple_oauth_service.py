from datetime import datetime
from typing import Any, Dict, List, Optional

import jwt
import requests

# from jwt.algorithms import RSAAlgorithm
# from jwt import algorithms
from jwt import PyJWKClient
from loguru import logger

from app.core.exceptions import (
    AppleKeyFetchError,
    InvalidSocialToken,
    InvalidSocialUID,
)
from app.settings import settings


class AppleOAuthService:
    """Service to handle Apple OAuth verification."""

    NAME = "apple"
    APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"
    ISSUER = "https://appleid.apple.com"

    def __init__(self, id_token: str, platform: str):
        self.id_token = id_token
        self.platform = platform
        self.uid: Optional[str] = None
        self.email: Optional[str] = None
        self.expiry: Optional[datetime] = None

    async def get_client_id(self) -> str:
        if self.platform == "ios":
            return settings.apple_ios_client_id
        return settings.apple_client_id

    async def _get_apple_public_keys(self) -> List[Dict[str, Any]]:
        """Fetch Apple's public keys."""
        # In a real production environment, checking Redis first would be better
        # But for this implementation we will fetch directly for simplicity given the scope
        # If Redis was strictly required for keys, we would inject it.
        try:
            response = requests.get(self.APPLE_PUBLIC_KEY_URL)
            response.raise_for_status()
            return response.json().get("keys", [])
        except Exception as e:
            logger.error(f"Failed to fetch Apple public keys: {e}")
            raise AppleKeyFetchError()

    async def _get_key_by_kid(
        self,
        keys: List[Dict[str, Any]],
        kid: str,
    ) -> Optional[Dict[str, Any]]:
        for key in keys:
            if key.get("kid") == kid:
                return key
        return None

    async def verify_id_token(self, uid: str) -> Any:
        """
        Verify the Apple ID Token.
        """

        try:
            jwk_client = PyJWKClient(self.APPLE_PUBLIC_KEY_URL)
            signing_key = jwk_client.get_signing_key_from_jwt(self.id_token)

            decoded = jwt.decode(
                self.id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=await self.get_client_id(),
                issuer=self.ISSUER,
                options={"verify_exp": True},
            )
            exp_raw: Optional[Any] = decoded.get("exp")
            if decoded.get("sub") != uid:
                raise InvalidSocialUID()

            self.uid = decoded.get("sub")
            self.email = decoded.get("email")
            if exp_raw is not None:
                self.expiry = datetime.utcfromtimestamp(float(exp_raw))
            else:
                self.expiry = None

        except jwt.ExpiredSignatureError:
            logger.error("Apple ID Token expired")
            raise InvalidSocialToken()

        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid Apple Token: {e}")
            raise InvalidSocialToken()

        except Exception as e:
            logger.exception(f"Unexpected error during Apple verification: {e}")
            raise InvalidSocialToken()

    async def get_email(self) -> Any:
        return self.email

    async def get_name(self) -> Any:
        # Apple ID token does not contain name.
        # Name is sent only on first login in a separate JSON object.
        # Since our schema doesn't capture it currenty, we return None or email prefix.
        return None

    async def get_uid(self) -> Any:
        return self.uid

    async def get_token(self) -> Any:
        return self.id_token

    async def get_expiry(self) -> Any:
        return self.expiry
