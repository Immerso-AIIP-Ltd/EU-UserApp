import json
from asyncio.log import logger

import requests

from app.core.exceptions.exceptions import CommServiceAPICallFailed


def call_communication_api(url, payload, method="POST"):
    """This method is used for calling comm service urls"""

    headers = {
        "Content-Type": "application/json",
        # 'x-api-client': settings.COMM_SERVICE_X_API_CLIENT,
        # 'x-service-token': settings.COMM_SERVICE_X_SERVICE_TOKEN,
    }

    response = requests.request(method, url, data=json.dumps(payload), headers=headers)
    if response.status_code != 200:
        logger.info("COMM API CALL",
                    extra={"server_response": response.text, "server_response_code": response.status_code})
        raise CommServiceAPICallFailed()
    logger.info("COMM API CALL", extra={"server_response": response.json()})
    return response.json()
