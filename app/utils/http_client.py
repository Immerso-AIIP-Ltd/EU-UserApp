import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class HttpClient:
    """Generic configuration for the HTTP Client."""

    _client: Optional[httpx.AsyncClient] = None
    _timeout: int = 10  # Default timeout in seconds

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Get or create a global httpx.AsyncClient for persistent connections."""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(timeout=cls._timeout)
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Close the HTTP client."""
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None

    @classmethod
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def make_request(
        cls,
        url: str,
        method: str = "POST",
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            url (str): The URL to request.
            method (str): HTTP method (default: "POST").
            json (dict): JSON payload.
            headers (dict): Request headers.
            params (dict): Query parameters.
            timeout (int): Request timeout in seconds.

        Returns:
            dict: The JSON response.

        Raises:
            httpx.HTTPStatusError: If the response status code is 4xx or 5xx.
            httpx.RequestError: If an error occurs while requesting.
        """
        client = cls.get_client()
        local_timeout = timeout if timeout is not None else cls._timeout

        try:
            logger.info(f"Making {method} request to {url}")
            response = await client.request(
                method=method,
                url=url,
                json=json,
                headers=headers,
                params=params,
                timeout=local_timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error occurred: {e.response.status_code} - {e.response.text}",
            )
            # You might want to return None or raise a custom exception here
            # depending on how you want to handle failures in the caller.
            # For now, relying on raise_for_status to raise.
            raise
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during HTTP request: {e}")
            raise
