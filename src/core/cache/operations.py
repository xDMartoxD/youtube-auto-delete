"""Basic cache operations (string-based)."""

import logging

import redis.asyncio as aioredis

from src.core.cache.client import get_redis_client

logger = logging.getLogger(__name__)


async def get_cache(key: str) -> str | None:
    """
    Get value from cache by key.

    Args:
        key: Cache key

    Returns:
        Cached value as string, or None if not found or error
    """
    try:
        client = await get_redis_client()
        return await client.get(key)
    except (aioredis.RedisError, aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.warning(f"Cache get error for key {key}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in cache get for key {key}: {e}")
        return None


async def set_cache(key: str, value: str, expire: int | None = None) -> bool:
    """
    Set value in cache with optional expiration.

    Args:
        key: Cache key
        value: Value to cache (must be string)
        expire: Expiration time in seconds (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        client = await get_redis_client()
        if expire:
            await client.setex(key, expire, value)
        else:
            await client.set(key, value)
        return True
    except (aioredis.RedisError, aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in cache set for key {key}: {e}")
        return False


async def delete_cache(key: str) -> bool:
    """
    Delete key from cache.

    Args:
        key: Cache key to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        client = await get_redis_client()
        await client.delete(key)
        return True
    except (aioredis.RedisError, aioredis.ConnectionError, aioredis.TimeoutError) as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in cache delete for key {key}: {e}")
        return False

