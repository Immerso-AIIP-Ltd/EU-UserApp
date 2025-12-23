import requests
import json
import uuid

# Base URL
BASE_URL = "http://0.0.0.0:8880/user/v1/user/login"

# Standard Headers
HEADERS = {
    "x-api-client": "android",
    "x-device-id": "test-device-id",
    "x-platform": "android",
    "x-country": "IN",
    "x-app-version": "1.0.0",
    "x-api-token": "test-api-token"
}

def test_login_user_not_found():
    print("\n--- Testing Login: User Not Found ---")
    payload = {
        "email": f"nonexistent_{uuid.uuid4()}@example.com",
        "password": "some_password"
    }
    response = requests.post(BASE_URL, json=payload, headers=HEADERS)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_login_incorrect_password():
    print("\n--- Testing Login: Incorrect Password ---")
    # This requires a user to exist in the DB. 
    # For now, we test the error propagation.
    payload = {
        "email": "test@example.com", # Assuming this exists or we catch the 404/401
        "password": "wrong_password"
    }
    response = requests.post(BASE_URL, json=payload, headers=HEADERS)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_login_success():
    print("\n--- Testing Login: Success ---")
    payload = {
        "email": "test@example.com",
        "password": "Pass@122"
    }
    response = requests.post(BASE_URL, json=payload, headers=HEADERS)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_login_missing_fields():
    print("\n--- Testing Login: Missing Fields (422) ---")
    payload = {
        "password": "some_password"
    }
    response = requests.post(BASE_URL, json=payload, headers=HEADERS)
    print(f"Status Code: {response.status_code}")
    # print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    test_login_user_not_found()
    test_login_missing_fields()
    # The following require actual DB setup if not mocked
    test_login_incorrect_password()
    test_login_success()
