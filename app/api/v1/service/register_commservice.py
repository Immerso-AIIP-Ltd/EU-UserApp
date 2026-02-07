import logging
from typing import Any, Dict

import httpx

from app.core.constants import (
    CommServiceConfig,
    HeaderKeys,
    HeaderValues,
    HTTPMethods,
    HTTPStatus,
    LogKeys,
)
from app.core.exceptions.exceptions import CommServiceAPICallFailedError

logger = logging.getLogger(__name__)


_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create a global httpx.AsyncClient for persistent connections."""
    global _http_client  # noqa: PLW0603
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=CommServiceConfig.TIMEOUT)
    return _http_client


async def call_communication_api(
    url: str,
    payload: Dict[str, Any],
    method: str = HTTPMethods.POST,
    headers: Dict[str, str] | None = None,
) -> Any:
    """Call communication API using persistent httpx client."""
    if headers is None:
        headers = {HeaderKeys.CONTENT_TYPE: HeaderValues.APPLICATION_JSON}

    client = get_http_client()
    try:
        response = await client.request(
            method,
            url,
            json=payload,
            headers=headers,
        )
    except Exception as e:
        logger.error(f"Failed to call communication API: {e}")
        raise CommServiceAPICallFailedError from e

    if response.status_code != HTTPStatus.OK:
        error_detail = response.text
        logger.error(
            f"Communication API returned {response.status_code}: {error_detail}",
        )
        logger.info(
            CommServiceConfig.LOGGER_MSG,
            extra={
                LogKeys.SERVER_RESPONSE: error_detail,
                LogKeys.SERVER_RESPONSE_CODE: response.status_code,
            },
        )
        raise CommServiceAPICallFailedError

    result = response.json()
    logger.info(
        CommServiceConfig.LOGGER_MSG,
        extra={LogKeys.SERVER_RESPONSE: result},
    )
    return result
