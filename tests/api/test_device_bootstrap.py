import base64
import json
import os
import time
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from httpx import AsyncClient

from app.api.queries import UserQueries
from app.api.v1.service.fusionauth_service import FusionAuthService

warnings.filterwarnings("ignore", category=RuntimeWarning)


# Helper to generate keys
def generate_rsa_keys() -> tuple[object, object, str]:
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


# Overrides for DB
@pytest.fixture(scope="module")
async def _engine() -> MagicMock:
    yield MagicMock()


@pytest.fixture
async def dbsession() -> AsyncMock:
    yield AsyncMock()


async def async_val(val: object) -> object:
    return val


@pytest.mark.anyio
async def test_bootstrap_device_success(client: AsyncClient) -> None:
    # 1. Setup Keys
    server_priv_key_obj, server_pub_key_obj, server_priv_pem = generate_rsa_keys()

    # 2. Prepare Payload
    install_id = "test-uuid-1234"
    timestamp = int(time.time())
    data_payload = {
        "install_id": install_id,
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
        ) + encryptor.finalize()
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
    with patch("app.api.v1.device.views.settings") as mock_settings, patch.object(
        FusionAuthService, "get_key",
    ) as mock_get_key, patch(
        "app.api.v1.device.views.execute_query",
    ) as mock_execute_query:

        mock_settings.fusionauth_bootstrap_key_id = "test-key-id"
        mock_get_key.return_value = {"privateKey": server_priv_pem}

        async def query_side_effect(
            query: object, *args: object, **kwargs: object,
        ) -> object:
            if query == UserQueries.CHECK_DEVICE_EXISTS:
                return []
            return [{"device_id": install_id, "id": 123}]

        mock_execute_query.side_effect = query_side_effect

        response = await client.post(
            "/user/v1/device/device_registration", json=request_payload,
        )

        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json["success"] is True
        assert resp_json["data"]["device_ref"] == install_id
        assert resp_json["data"]["status"] == "REGISTERED"


@pytest.mark.anyio
async def test_bootstrap_device_expired(client: AsyncClient) -> None:
    # 1. Setup Keys
    server_priv_key_obj, server_pub_key_obj, server_priv_pem = generate_rsa_keys()

    # 2. Prepare Payload (EXPIRED)
    install_id = "test-uuid-expired"
    timestamp = int(time.time()) - 35  # 35 seconds old
    data_payload = {
        "install_id": install_id,
        "timestamp": timestamp,
        "platform": "android",
    }

    aes_key = os.urandom(32)
    encrypted_key_bytes = server_pub_key_obj.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_key = base64.b64encode(encrypted_key_bytes).decode("utf-8")

    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = (
        encryptor.update(
            json.dumps(data_payload).encode("utf-8"),
        ) + encryptor.finalize()
    )
    tag = encryptor.tag
    full_encrypted_data = iv + ciphertext + tag
    encrypted_data_str = base64.b64encode(full_encrypted_data).decode("utf-8")

    request_payload = {
        "key": encrypted_key,
        "data": encrypted_data_str,
    }

    with patch("app.api.v1.device.views.settings") as mock_settings, patch.object(
        FusionAuthService, "get_key",
    ) as mock_get_key, patch(
        "app.api.v1.device.views.execute_query",
    ) as mock_execute_query:

        mock_settings.fusionauth_bootstrap_key_id = "test-key-id"
        mock_get_key.return_value = {"privateKey": server_priv_pem}

        response = await client.post(
            "/user/v1/device/device_registration", json=request_payload,
        )

        assert response.status_code == 403
        assert "expired" in response.json()["detail"]

        # Verify DB was NOT called
        mock_execute_query.assert_not_called()
