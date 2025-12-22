import jwt
import requests
import json

# Configuration
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
USER_ID = "00000000-0000-0000-0000-000000000000"  # Dummy ID

# Generate Token
payload = {
    "user_id": USER_ID,
    "email": "test@example.com"
}
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Headers
headers = {
    "Authorization": f"Bearer {token}",
    "x-api-client": "android",
    "x-device-id": "test-device-id",
    "x-platform": "android",
    "x-country": "IN",
    "x-app-version": "1.0.0",
    "x-api-token": "test-api-token"
}

base_url = "http://0.0.0.0:8880/user/v1/user_profile/profile"

def test_get_profile():
    print("\n--- Testing GET Profile ---")
    response = requests.get(base_url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_update_profile():
    print("\n--- Testing PUT Update Profile ---")
    body = {
        "name": "Updated Name",
        "gender": "M",
        "about_me": "Hello from test!",
        "birth_date": "2000-01-01",
        "nick_name": "tester",
        "country": "IN",
        "avatar_id": 1,
        "profile_image": None
    }
    response = requests.put(base_url, headers=headers, json=body)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    test_get_profile()
    test_update_profile()
