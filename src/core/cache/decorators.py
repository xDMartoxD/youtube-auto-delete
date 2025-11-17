"""Cache decorators for function result caching."""

import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from src.core.cache.operations import get_cache, set_cache
from src.core.cache.serialization import get_json_cache, set_json_cache
from src.core.cache.utils import cache_key

logger = logging.getLogger(__name__)

T = TypeVar("T")


def cached(
    key_prefix: str,
    expire: int = 3600,
    serialize_json: bool = True,
):
    """
    Decorator to cache function results in Redis.

    Args:
        key_prefix: Prefix for cache key
        expire: Cache expiration time in seconds (default: 1 hour)
        serialize_json: Whether to serialize/deserialize as JSON (default: True)

    Returns:
        Decorator function

    Example:
        @cached("user_profile", expire=1800)
        async def get_user_profile(user_id: str):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = cache_key(key_prefix, *args, **kwargs)

            # Try to get from cache
            if serialize_json:
                cached_value = await get_json_cache(cache_key_str)
            else:
                cached_value = await get_cache(cache_key_str)

            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key_str}")
                return cached_value

            # Cache miss, execute function
            logger.debug(f"Cache miss for key: {cache_key_str}")
            result = await func(*args, **kwargs)

            # Store in cache
            if serialize_json:
                await set_json_cache(cache_key_str, result, expire)
            else:
                if isinstance(result, str):
                    await set_cache(cache_key_str, result, expire)
                else:
                    logger.warning(
                        f"Cannot cache non-string value for key {cache_key_str}"
                    )

            return result

        return wrapper

    return decorator

