import jwt
import requests
import json

# Configuration
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
USER_ID = "00000000-0000-0000-0000-000000000000"  # Dummy ID

# Generate Token
payload = {"user_id": USER_ID, "email": "test@example.com"}
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Headers
headers = {
    "Authorization": f"Bearer {token}",
    "x-api-client": "android",
    "x-device-id": "test-device-id",
    "x-platform": "android",
    "x-country": "IN",
    "x-app-version": "1.0.0",
    "x-api-token": "test-api-token",
}

base_url = "http://0.0.0.0:8880/user/v1/user_profile/update_email_mobile"


def test_update_email():
    print("\n--- Testing POST Update Email ---")
    body = {"email": "newemail@example.com", "mobile": None, "calling_code": None}
    response = requests.post(base_url, headers=headers, json=body)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_update_mobile():
    print("\n--- Testing POST Update Mobile ---")
    body = {"email": None, "mobile": "9876543210", "calling_code": "+91"}
    response = requests.post(base_url, headers=headers, json=body)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_invalid_update():
    print("\n--- Testing POST Invalid Update (Both) ---")
    body = {"email": "bad@example.com", "mobile": "1234567890", "calling_code": "+1"}
    response = requests.post(base_url, headers=headers, json=body)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    test_update_email()
    test_update_mobile()
    test_invalid_update()
