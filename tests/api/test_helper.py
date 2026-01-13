import uuid
from typing import Any, Dict, Optional

from httpx import AsyncClient

from app.core.constants import HeaderKeys


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())

def get_auth_headers(
    token: Optional[str] = None,
    device_id: str = "device-123",
    platform: str = "android",
    country: str = "US",
    version: str = "1.0.0",
) -> Dict[str, str]:
    """Generate common request headers."""
    headers = {
        HeaderKeys.X_DEVICE_ID: device_id,
        HeaderKeys.X_PLATFORM: platform,
        HeaderKeys.X_COUNTRY: country,
        HeaderKeys.X_APP_VERSION: version,
        HeaderKeys.X_API_CLIENT: "test-client",
        "x-request-id": generate_request_id(),
    }
    if token:
        headers[HeaderKeys.X_API_TOKEN] = token
    return headers

async def assert_endpoint_success(
    client: AsyncClient,
    method: str,
    url: str,
    expected_message: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    expected_status: int = 200,
) -> Dict[str, Any]:
    """Assert that an endpoint returns a successful response."""
    if headers is None:
        headers = get_auth_headers()


    if method.upper() == "POST":
        response = await client.post(url, json=payload, headers=headers)
    elif method.upper() == "GET":
        response = await client.get(url, headers=headers)
    elif method.upper() == "PUT":
        response = await client.put(url, json=payload, headers=headers)
    elif method.upper() == "PATCH":
        response = await client.patch(url, json=payload, headers=headers)
    elif method.upper() == "DELETE":
        response = await client.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")

    msg = (
        f"Expected {expected_status}, got {response.status_code}. "
        f"Body: {response.text}"
    )
    assert response.status_code == expected_status, msg
    data = response.json()
    assert data["success"] is True
    assert data["message"] == expected_message
    return data

async def assert_endpoint_error(
    client: AsyncClient,
    method: str,
    url: str,
    expected_status: int,
    expected_message: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Assert that an endpoint returns an error response."""
    if headers is None:
        headers = get_auth_headers()

    if method.upper() == "POST":
        response = await client.post(url, json=payload, headers=headers)
    elif method.upper() == "GET":
        response = await client.get(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method for error assertion helper: {method}")

    assert response.status_code == expected_status
    data = response.json()
    assert data["success"] is False
    if expected_message:
        assert data["message"] == expected_message
    return data

async def assert_missing_headers(
    client: AsyncClient,
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Assert that the endpoint fails when headers are missing."""
    if method.upper() == "POST":
        response = await client.post(url, json=payload, headers={})
    elif method.upper() == "GET":
        response = await client.get(url, headers={})
    else:
        response = await client.request(method, url, headers={})

    assert response.status_code == 422
