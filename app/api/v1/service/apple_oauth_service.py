import json
from datetime import datetime
from typing import Dict, List, Optional

import jwt
import requests
from jwt.algorithms import RSAAlgorithm
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

    def get_client_id(self) -> str:
        if self.platform == "ios":
            return settings.apple_ios_client_id
        return settings.apple_client_id

    def _get_apple_public_keys(self) -> List[Dict]:
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

    def _get_key_by_kid(self, keys: List[Dict], kid: str) -> Optional[Dict]:
        for key in keys:
            if key.get("kid") == kid:
                return key
        return None

    async def verify_id_token(self, uid: str):
        """
        Verify the Apple ID Token.
        """
        try:
            # Get kid from header
            unverified_header = jwt.get_unverified_header(self.id_token)
            kid = unverified_header.get("kid")

            if not kid:
                raise InvalidSocialToken()

            keys = self._get_apple_public_keys()
            key_data = self._get_key_by_kid(keys, kid)

            if not key_data:
                logger.error(f"Apple public key not found for kid: {kid}")
                raise InvalidSocialToken()

            public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))

            # Verify token
            decoded = jwt.decode(
                self.id_token,
                public_key,
                algorithms=["RS256"],
                audience=self.get_client_id(),
                issuer=self.ISSUER,
                options={"verify_exp": True},
            )

            if decoded.get("sub") != uid:
                raise InvalidSocialUID()

            self.uid = decoded.get("sub")
            self.email = decoded.get("email") # Email might be missing if private relay is used/already shared
            self.expiry = datetime.utcfromtimestamp(decoded.get("exp"))

        except jwt.ExpiredSignatureError:
            logger.error("Apple ID Token expired")
            raise InvalidSocialToken()
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid Apple Token: {e}")
            raise InvalidSocialToken()
        except Exception as e:
            logger.exception(f"Unexpected error during Apple verification: {e}")
            raise InvalidSocialToken()

    def get_email(self):
        return self.email

    def get_name(self):
        # Apple ID token does not contain name.
        # Name is sent only on first login in a separate JSON object.
        # Since our schema doesn't capture it currenty, we return None or email prefix.
        return None

    def get_uid(self):
        return self.uid

    def get_token(self):
        return self.id_token

    def get_expiry(self):
        return self.expiry
