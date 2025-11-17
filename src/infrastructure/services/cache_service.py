"""Cache service for infrastructure layer - handles Redis caching operations."""

import logging
from typing import Any, TypeVar

from src.core.cache import get_json_cache, set_json_cache, cache_key

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheService:
    """
    Infrastructure service for caching operations.
    Encapsulates cache logic and provides a clean interface for application services.
    """

    async def get(
        self, key_prefix: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any] | None:
        """
        Get value from cache.

        Args:
            key_prefix: Prefix for cache key
            *args: Positional arguments to include in cache key
            **kwargs: Keyword arguments to include in cache key

        Returns:
            Cached value as dict, or None if not found
        """
        cache_key_str = cache_key(key_prefix, *args, **kwargs)
        cached_result = await get_json_cache(cache_key_str)
        if cached_result:
            logger.info(f"Cache hit for key: {cache_key_str}")
        else:
            logger.info(f"Cache miss for key: {cache_key_str}")
        return cached_result

    async def set(
        self,
        key_prefix: str,
        value: dict[str, Any],
        expire: int,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key_prefix: Prefix for cache key
            value: Value to cache (must be serializable to JSON)
            expire: Expiration time in seconds
            *args: Positional arguments to include in cache key
            **kwargs: Keyword arguments to include in cache key

        Returns:
            True if successful, False otherwise
        """
        cache_key_str = cache_key(key_prefix, *args, **kwargs)
        result = await set_json_cache(cache_key_str, value, expire)
        if result:
            logger.info(f"Cached value for key: {cache_key_str} (expires in {expire}s)")
        else:
            logger.warning(f"Failed to cache value for key: {cache_key_str}")
        return result

    async def get_or_set(
        self,
        key_prefix: str,
        fetch_func: Any,
        expire: int,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Get value from cache, or fetch and cache if not found.

        Args:
            key_prefix: Prefix for cache key
            fetch_func: Async function to fetch value if not in cache
            expire: Expiration time in seconds
            *args: Positional arguments for cache key and fetch_func
            **kwargs: Keyword arguments for cache key and fetch_func

        Returns:
            Cached or fetched value as dict
        """
        cached_result = await self.get(key_prefix, *args, **kwargs)
        if cached_result:
            return cached_result

        # Cache miss - fetch value
        result = await fetch_func(*args, **kwargs)

        # Convert to dict if it's a Pydantic model
        if hasattr(result, "model_dump"):
            result_dict = result.model_dump()
        elif isinstance(result, dict):
            result_dict = result
        else:
            logger.warning(f"Cannot cache non-dict/non-model value: {type(result)}")
            return result

        # Cache the result
        await self.set(key_prefix, result_dict, expire, *args, **kwargs)

        return result_dict
