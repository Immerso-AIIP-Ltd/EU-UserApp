import base64
import json
import os
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from httpx import AsyncClient

from app.api.queries import UserQueries
from app.api.v1.service.fusionauth_service import FusionAuthService
from tests.api.test_helper import assert_endpoint_success, get_auth_headers


# Helper to generate keys
def generate_rsa_keys() -> tuple[RSAPrivateKey, RSAPublicKey, str]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    return private_key, public_key, pem_private


@pytest.mark.anyio
async def test_bootstrap_device_success(client: AsyncClient) -> None:
    # 1. Setup Keys
    server_priv_key_obj, server_pub_key_obj, server_priv_pem = generate_rsa_keys()

    # 2. Prepare Payload
    install_id = "test-uuid-1234"
    timestamp = int(time.time())
    data_payload = {
        "serial_number": install_id,
        "timestamp": timestamp,
        "platform": "android",
        "device_name": "Test Device",
    }

    aes_key = os.urandom(32)

    # Encrypt AES Key
    encrypted_key_bytes = server_pub_key_obj.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_key = base64.b64encode(encrypted_key_bytes).decode("utf-8")

    # Encrypt Data (AES-GCM)
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = (
        encryptor.update(
            json.dumps(data_payload).encode("utf-8"),
        )
        + encryptor.finalize()
    )
    tag = encryptor.tag

    # Format: IV + Ciphertext + Tag
    full_encrypted_data = iv + ciphertext + tag
    encrypted_data_str = base64.b64encode(full_encrypted_data).decode("utf-8")

    request_payload = {
        "key": encrypted_key,
        "data": encrypted_data_str,
    }

    # 3. Patching and Execution
    with patch("app.utils.security.settings") as mock_settings, patch.object(
        FusionAuthService,
        "get_key",
        new_callable=MagicMock,  # SYNC function
    ) as mock_get_key, patch(
        "app.api.v1.device.views.execute_query",
        new_callable=AsyncMock,
    ) as mock_execute_query:

        mock_settings.fusionauth_bootstrap_key_id = "test-key-id"
        mock_get_key.return_value = {"privateKey": server_priv_pem}

        async def query_side_effect(query: Any, *args: Any, **kwargs: Any) -> Any:
            if query == UserQueries.CHECK_DEVICE_EXISTS:
                return []
            return [{"device_id": install_id, "id": 123}]

        mock_execute_query.side_effect = query_side_effect

        headers = get_auth_headers(device_id=install_id)

        await assert_endpoint_success(
            client,
            "POST",
            "/user/v1/device/device_registration",
            "Device registered successfully",
            payload=request_payload,
            headers=headers,
        )
