import uuid
from datetime import datetime, timedelta

import jwt
import pytz

from app.core.constants import AuthConfig, RequestParams
from app.settings import settings


def get_random_token() -> str:
    """Generates a valid JWT token for a random simulated user."""
    user_id = str(uuid.uuid4())
    secret = settings.jwt_secret_key
    expiry = datetime.now(pytz.utc) + timedelta(days=settings.user_token_days_to_expire)

    token_payload = {
        RequestParams.UUID: user_id,
        RequestParams.EXP: expiry,
    }

    return jwt.encode(
        token_payload,
        secret,
        algorithm=AuthConfig.ALGORITHM,
    )
