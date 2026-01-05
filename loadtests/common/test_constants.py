# This file contains shared constants for the load tests.

# Shared data, populated by the bootstrap process or static definition
COUNTRY_IDS = ["IN", "US", "GB"]
LANGUAGE_KEYS = ["en"]
LANGUAGE_CODES = ["en"]
TEXT_KEYS = {}

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

# Bootstrap parameters
BOOTSTRAP_COUNTRIES_PARAMS = {"appname": "android_app", "limit": 100}
BOOTSTRAP_LANGUAGES_PARAMS = {"limit": 100, "active": "True"}
BOOTSTRAP_TRANSLATIONS_PARAMS = {"page": 1, "limit": 100}
