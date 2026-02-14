import asyncio
from typing import Any, Dict, Optional

import httpx
from fastapi import Request
from loguru import logger

from app.settings import settings


async def call_reward_api_async(
    request: Request,
    action_type: str,
    retries: int = 3,
    delay: int = 2,
) -> Optional[Dict[str, Any]]:
    """Call Reward API asynchronously with retry support."""

    user_id = request.headers.get("x-user-id")
    reward_url: str | None = settings.reward_api_url

    if not reward_url:
        logger.error("Missing reward_api_url.")
        return None

    reward_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "x-user-id": user_id or "",
    }

    reward_data = {"action_type": action_type}
    timeout = httpx.Timeout(10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, retries + 1):
            try:
                response = await client.post(
                    reward_url,
                    json=reward_data,
                    headers=reward_headers,
                )

                if response.status_code == 200:
                    result: Dict[str, Any] = response.json()
                    logger.info(
                        "Reward API success action=%s attempt=%s",
                        action_type,
                        attempt,
                    )
                    return result

                logger.warning(
                    "Reward API failed status=%s action=%s attempt=%s",
                    response.status_code,
                    action_type,
                    attempt,
                )

            except httpx.RequestError as exc:
                logger.error(
                    "Reward API error action=%s attempt=%s error=%s",
                    action_type,
                    attempt,
                    str(exc),
                )

            if attempt < retries:
                await asyncio.sleep(delay)

    logger.error("Reward API failed after %s attempts action=%s", retries, action_type)
    return None
