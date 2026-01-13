import base64
import json
import os
import time
from typing import Any

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from loguru import logger

from app.settings import settings

_public_key_cache = None


def _get_public_key() -> Any:
    """
    Retrieve the public key for encryption.

    1. Try trying to derive from local private key in settings.
    2. Fallback to fetching from FusionAuth.
    """
    global _public_key_cache  # noqa: PLW0603
    if _public_key_cache:
        return _public_key_cache

    # 1. Try local derivation
    if settings.decryption_private_key_b64:
        try:
            private_key_pem_str = base64.b64decode(
                settings.decryption_private_key_b64,
            ).decode("utf-8")
            private_key = serialization.load_pem_private_key(
                private_key_pem_str.encode(),
                password=None,
                backend=default_backend(),
            )
            public_key = private_key.public_key()
            _public_key_cache = public_key
            logger.info("Loaded public key from local settings.")
            return public_key
        except Exception as e:
            logger.warning(f"Failed to load local private key: {e}")

    # 2. Fallback to FusionAuth fetch
    try:
        url = f"{settings.fusionauth_url}/api/jwt/public-key"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            keys_map = response.json().get("publicKeys", {})
            if keys_map:
                kid = settings.fusionauth_bootstrap_key_id
                pem = keys_map.get(kid) if kid else next(iter(keys_map.values()))

                if pem:
                    public_key = serialization.load_pem_public_key(
                        pem.encode(),
                        backend=default_backend(),
                    )
                    _public_key_cache = public_key
                    return public_key
    except Exception as e:
        logger.error(f"Failed to fetch public key from FusionAuth: {e}")

    raise Exception("Could not retrieve public key for encryption.")


def encrypt_payload(data: dict) -> dict:
    """Encrypts the payload using Hybrid Encryption (RSA + AES)."""
    # 1. Fetch Public Key
    public_key = _get_public_key()
    if not public_key:
        raise Exception("Could not retrieve public key for encryption.")

    # 2. Generate AES-256 Key & IV
    aes_key = os.urandom(32)
    iv = os.urandom(12)

    # 3. Add Timestamp (Required for anti-replay)
    if "timestamp" not in data:
        data["timestamp"] = int(time.time())

    # 4. Encrypt AES Key with RSA
    # public_key is already an Object
    encrypted_key = base64.b64encode(
        public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        ),
    ).decode("utf-8")

    # 5. Encrypt Data with AES-GCM
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = (
        encryptor.update(json.dumps(data).encode("utf-8")) + encryptor.finalize()
    )

    # Format: IV + Ciphertext + TAG
    encrypted_data = base64.b64encode(iv + ciphertext + encryptor.tag).decode("utf-8")

    return {"key": encrypted_key, "data": encrypted_data}
