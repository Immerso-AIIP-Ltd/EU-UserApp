import base64
import json
import os
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# 1. Generate a Test RSA Key Pair
private_key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
public_key = private_key.public_key()

# 2. Format the Private Key for your .env
priv_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
priv_b64 = base64.b64encode(priv_pem).decode("utf-8")

print("-" * 30)
print("ADD THIS TO YOUR .env AND RESTART THE APP:")
print(f"APP_DECRYPTION_PRIVATE_KEY_B64={priv_b64}")
print("-" * 30)

# 3. Your Raw Data
data_payload = {
    "device_id": "12345-67890-abcde-dfgher",
    "device_name": "Web Chrome",
    "device_type": "desktop",
    "platform": "web",
    "timestamp": int(time.time()),  # REQUIRED
    "push_token": "token123",
    "device_ip": "196.168.1.221",
}

# 4. Hybrid Encryption Logic
aes_key = os.urandom(32)
# Encrypt AES Key with RSA Public Key
enc_key_bytes = public_key.encrypt(
    aes_key,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    ),
)
encrypted_key = base64.b64encode(enc_key_bytes).decode("utf-8")

# Encrypt Data with AES-GCM
iv = os.urandom(12)
cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv), backend=default_backend())
encryptor = cipher.encryptor()
ciphertext = (
    encryptor.update(json.dumps(data_payload).encode("utf-8")) + encryptor.finalize()
)
full_data = iv + ciphertext + encryptor.tag
encrypted_data = base64.b64encode(full_data).decode("utf-8")

# 5. Output for Postman
print("\nPASTE THIS BODY INTO POSTMAN:")
print(json.dumps({"key": encrypted_key, "data": encrypted_data}, indent=4))
