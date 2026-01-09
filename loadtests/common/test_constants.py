# This file contains shared constants for the load tests.

# Static data for tasks
PLATFORMS = ["android", "ios"]
APPNAMES = ["android_app"]
TEST_APP_NAME = "android_app"

# Headers
# Matching app/utils/validate_headers.py CommonHeaders
DEFAULT_HEADERS = {
    "x-api-client": "android_app",
    "x-device-id": "locust-bootstrap-device-id",
    "x-platform": "android",
    "x-country": "IN",
    "x-app-version": "1.0.0",
}
JSON_HEADERS = {
    **DEFAULT_HEADERS,
    "Content-Type": "application/json",
    "accept": "application/json",
}
