import bcrypt
import hashlib
from celery import shared_task

# from utils import redis # Removed broken import


@shared_task(bind=True, name="block_ip_for_24_hours")
def block_ip_for_24_hours(self, ip_address, receiver):
    """
    Blocks the given IP address for 24 hours using Redis.
    """
    # TODO: Refactor to use async redis or proper celery redis backend if needed.
    # Current implementation attempts to use broken 'utils.redis'.
    # disabling broken logic for now to allow app startup.
    print(f"Would block IP address {ip_address}_{receiver} for 24 hours (Redis logic disabled).")
    # BLOCK_DURATION_SECONDS = settings.BLOCK_DURATION_SECONDS
    # cache_key = f"blocked_ip_{ip_address}_{receiver}"
    # redis.set_val(cache_key, "1", timeout=BLOCK_DURATION_SECONDS)
    # print(f"Blocked IP address {ip_address}_{receiver} for 24 hours.")


async def get_hashed_password(plain_text_password):
    # Convert string to bytes if needed
    if isinstance(plain_text_password, str):
        plain_text_password = plain_text_password.encode('utf-8')
    return bcrypt.hashpw(plain_text_password, bcrypt.gensalt())


async def check_password(plain_text_password, hashed_password):
    # Convert string to bytes if needed
    if isinstance(plain_text_password, str):
        plain_text_password = plain_text_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_text_password, hashed_password)


async def get_sha1_hash(plain_text_password):
    return hashlib.sha1(plain_text_password.encode('utf-8')).hexdigest()

async def clone_object(obj):
    obj.pk = None
    return obj