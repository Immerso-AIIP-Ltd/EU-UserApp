import httpx
from loguru import logger

from app.settings import settings


async def assign_free_plan_to_user(user_id: str | int) -> None:
    """Assign a free plan to the user via external API."""
    try:
        url = settings.app_assign_free_plan_api_url
        headers = {
            "x-platform": "web",
            "x-user-id": str(user_id),
            "x-public-key": settings.app_assign_free_plan_public_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json={}, timeout=10.0)
            response.raise_for_status()

        logger.info(f"Assigned free plan to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to assign free plan to user {user_id}: {e}")
