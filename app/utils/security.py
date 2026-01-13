import base64
import contextlib
import json
import time
from typing import Any, Dict

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.api.v1.service.fusionauth_service import FusionAuthService
from app.core.constants import ErrorMessages
from app.core.exceptions.exceptions import (
    BootstrapKeyIdNotConfiguredError,
    RequestTimeoutError,
    ValidationError,
)
from app.settings import settings


class SecurityService:
    """Utility service for handling encryption/decryption."""

    @staticmethod
    def _get_private_key_pem(private_key_pem: str | None = None) -> str:
        """Helper to retrieve private key PEM from settings or FusionAuth."""
        if private_key_pem:
            return private_key_pem

        # 1. Check for local private key in settings (from env)
        if settings.decryption_private_key_b64:
            with contextlib.suppress(Exception):
                return base64.b64decode(settings.decryption_private_key_b64).decode(
                    "utf-8",
                )

        # 2. Fetch from FusionAuth if still not provided
        key_id = settings.fusionauth_bootstrap_key_id
        if not key_id:
            raise BootstrapKeyIdNotConfiguredError

        key_obj = FusionAuthService.get_key(key_id)
        private_key_pem = key_obj.get("privateKey")
        if not private_key_pem:
            raise ValidationError("Private key not found in FusionAuth")

        return private_key_pem

    @staticmethod
    def decrypt_payload(
        encrypted_key: str,
        encrypted_data: str,
        private_key_pem: str | None = None,
    ) -> Dict[str, Any]:
        """
        Decrypts a hybrid-encrypted payload.

        1. Decrypts AES key using RSA Private Key.
        2. Decrypts Data using AES-256-GCM.
        3. Validates timestamp.
        """
        private_key_pem = SecurityService._get_private_key_pem(private_key_pem)

        # 1. Decrypt AES Key
        try:
            encrypted_aes_key = base64.b64decode(encrypted_key)
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend(),
            )

            if not isinstance(private_key, rsa.RSAPrivateKey):
                raise ValidationError("Invalid private key type")

            aes_key = private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
        except Exception as e:
            # User request: return timeout-like error on decryption failure
            raise RequestTimeoutError(ErrorMessages.REQUEST_EXPIRED) from e

        # 2. Decrypt Payload (AES-GCM)
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
            if len(encrypted_bytes) < 28:  # 12 (IV) + 16 (Tag)
                raise ValidationError("Invalid encrypted data length")

            iv = encrypted_bytes[:12]
            tag = encrypted_bytes[-16:]
            ciphertext = encrypted_bytes[12:-16]

            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.GCM(iv, tag),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()
            decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()

            payload_json = json.loads(decrypted_bytes.decode("utf-8"))
        except Exception as e:
            # User request: return timeout-like error on decryption failure
            raise RequestTimeoutError(ErrorMessages.REQUEST_EXPIRED) from e

        # 3. Validate Timestamp
        timestamp = payload_json.get("timestamp")
        if not timestamp:
            raise RequestTimeoutError(ErrorMessages.TIMESTAMP_MISSING)

        now = int(time.time())
        if abs(now - int(timestamp)) > 30:  # 30 seconds leeway
            raise RequestTimeoutError(ErrorMessages.REQUEST_EXPIRED)

        return payload_json
