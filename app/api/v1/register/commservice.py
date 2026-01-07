import json
from asyncio.log import logger
from typing import Any, Dict

import requests

from app.core.constants import (
    CommServiceConfig,
    HeaderKeys,
    HeaderValues,
    HTTPMethods,
    HTTPStatus,
    LogKeys,
)
from app.core.exceptions.exceptions import CommServiceAPICallFailedError


async def call_communication_api(
    url: str,
    payload: Dict[str, Any],
    method: str = HTTPMethods.POST,
    headers: Dict[str, str] | None = None,
) -> Any:
    """Call external communication API with JSON payload."""
    if headers is None:
        headers = {HeaderKeys.CONTENT_TYPE: HeaderValues.APPLICATION_JSON}
    response = requests.request(
        method,
        url,
        data=json.dumps(payload),
        headers=headers,
        timeout=CommServiceConfig.TIMEOUT,
    )
    if response.status_code != HTTPStatus.OK:
        logger.info(
            CommServiceConfig.LOGGER_MSG,
            extra={
                LogKeys.SERVER_RESPONSE: response.text,
                LogKeys.SERVER_RESPONSE_CODE: response.status_code,
            },
        )
        raise CommServiceAPICallFailedError
    logger.info(
        CommServiceConfig.LOGGER_MSG,
        extra={LogKeys.SERVER_RESPONSE: response.json()},
    )
    return response.json()
