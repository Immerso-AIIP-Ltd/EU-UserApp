# module for helper functions for redis cache
import json
import logging
import traceback

from app.cache.dependencies import get_redis_connection


logger = logging.getLogger("redis")

def remove_uuid_device_token(uuid, platform, device_token):
    """
    Remove a specific device token from Redis for the given UUID & platform.
    """
    con = get_redis_connection("device_db2")
    uuid_str = str(uuid)

    try:
        current_data = con.get(uuid_str)
        tokens_by_platform = json.loads(current_data.decode("utf-8")) if current_data else {}
    except Exception:
        tokens_by_platform = {}

    tokens = tokens_by_platform.get(platform, [])

    if device_token in tokens:
        tokens.remove(device_token)

    # Update or delete platform entry
    if tokens:
        tokens_by_platform[platform] = tokens
        con.set(uuid_str, json.dumps(tokens_by_platform))
    else:
        # No tokens left for platform
        tokens_by_platform.pop(platform, None)
        if tokens_by_platform:
            con.set(uuid_str, json.dumps(tokens_by_platform))
        else:
            con.delete(uuid_str)


def save_device_token(device_id, device_token, timeout=None):
    con = get_redis_connection("device_db1")
    if timeout:
        con.set(device_id, device_token, ex=timeout)
    else:
        con.set(device_id, device_token)


def add_uuid_device_token(uuid, platform, device_token, timeout=None):
    con = get_redis_connection("device_db2")
    uuid_str = str(uuid)

    # Try to read existing JSON (dict of platforms)
    try:
        current_data = con.get(uuid_str)
        tokens_by_platform = json.loads(current_data.decode("utf-8")) if current_data else {}
    except Exception:
        tokens_by_platform = {}

    # Get token list for this platform
    tokens = tokens_by_platform.get(platform, [])

    if device_token not in tokens:
        tokens.append(device_token)

    # Update dict
    tokens_by_platform[platform] = tokens

    # Store back as JSON string
    con.set(uuid_str, json.dumps(tokens_by_platform))

    if timeout:
        con.expire(uuid_str, timeout)

def sadd(key, val):
    con = get_redis_connection("default")
    con.sadd(key, val)

def srem(key, val):
    con = get_redis_connection("default")
    con.srem(key, val)

def smembers(key):
    con = get_redis_connection("default")
    return [val.decode("utf-8") for val in con.smembers(key)]

def lpush(key, val):
    try:
        con = get_redis_connection("default")
        con.lpush(key, val)
    except Exception as e:
        logger.error(
            "UNABLE TO SAVE TOKEN TO REDIS",
            extra={
                "redis_error": {
                    "key": key,
                    "value": val,
                    "message": str(e),
                    "traceback": "".join(traceback.format_tb(e.__traceback__)),
                },
            },
        )


def get_list(key):
    con = get_redis_connection("default")
    return con.lrange(key, 0, -1)


def lrem(key, count, val):
    # removes the first count occurance of a value from list
    try:
        con = get_redis_connection("default")
        con.lrem(key, count, val)
    except Exception as e:
        logger.error(
            "UNABLE TO REMOVE TOKEN FROM REDIS",
            extra={
                "redis_error": {
                    "key": key,
                    "value": val,
                    "message": str(e),
                    "traceback": "".join(traceback.format_tb(e.__traceback__)),
                },
            },
        )


def set_dict(key, val, timeout=None):
    con = get_redis_connection("default")
    con.set(key, json.dumps(val), timeout)


def get_val(key):
    con = get_redis_connection("default")
    value = con.get(key)

    if value:
        return value.decode("utf-8")
    else:
        return None


def set_val(key, val, timeout=None):
    con = get_redis_connection("default")
    if timeout:
        con.set(key, val, timeout)
    else:
        con.set(key, val)


def remove_key(key):
    con = get_redis_connection("default")
    con.delete(key)


def incr_val(key):
    try:
        con = get_redis_connection("default")
        return con.incr(key)
    except Exception as e:
        logger.error(
            "UNABLE TO INCREMENT VALUE IN REDIS",
            extra={
                "redis_error": {
                    "key": key,
                    "message": str(e),
                    "traceback": "".join(traceback.format_tb(e.__traceback__)),
                },
            },
        )
        return None


def expire_key(key, timeout):
    try:
        con = get_redis_connection("default")
        con.expire(key, timeout)
    except Exception as e:
        logger.error(
            "UNABLE TO SET EXPIRY ON REDIS KEY",
            extra={
                "redis_error": {
                    "key": key,
                    "timeout": timeout,
                    "message": str(e),
                    "traceback": "".join(traceback.format_tb(e.__traceback__)),
                },
            },
        )
