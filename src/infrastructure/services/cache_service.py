"""Cache service for infrastructure layer - handles Redis caching operations."""

import logging
from typing import Any, TypeVar

from src.core.cache import (
    get_json_cache,
    set_json_cache,
    cache_key,
    invalidate_cache,
    PatternInvalidationStrategy,
)

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

    async def invalidate(
        self,
        key_prefix: str,
        use_pattern: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> int:
        """
        Invalidate cache entries.

        Args:
            key_prefix: Prefix for cache key to invalidate
            use_pattern: If True, invalidate all keys matching the pattern (e.g., "prefix:*")
                        If False, invalidate only the exact key
            *args: Positional arguments to include in cache key (only used when use_pattern=False)
            **kwargs: Keyword arguments to include in cache key

        Returns:
            Number of keys invalidated

        Examples:
            # Invalidate exact key
            await cache_service.invalidate("user_playlists", user_id="123", max_results=50)

            # Invalidate all keys with prefix (pattern-based)
            await cache_service.invalidate("playlist_videos", use_pattern=True)
            # This will invalidate: playlist_videos:*, playlist_videos:*:*, etc.

            # Invalidate all keys with prefix and specific kwargs
            await cache_service.invalidate("playlist_videos", playlist_id="123", use_pattern=True)
            # This will invalidate: playlist_videos:playlist_id:123:*
        """
        if use_pattern:
            # Use pattern-based invalidation
            if kwargs:
                # Build pattern with prefix and kwargs
                # e.g., "playlist_videos:playlist_id:123:*"
                base_key = cache_key(key_prefix, *args, **kwargs)
                pattern = f"{base_key}:*"
            else:
                # Invalidate all keys with this prefix
                pattern = f"{key_prefix}:*"

            strategy = PatternInvalidationStrategy()
            return await strategy.invalidate(pattern)
        else:
            # Use prefix-based invalidation for exact key
            # This uses the convenience function from core/cache
            return await invalidate_cache(key_prefix, *args, **kwargs)

    async def invalidate_by_filter(
        self,
        key_prefixes: list[str],
        filter_func: Any,
    ) -> int:
        """
        Invalidate cache entries by scanning keys with given prefixes and applying a filter.

        Args:
            key_prefixes: List of key prefixes to scan (e.g., ["playlist_videos", "playlist_videos_by_date"])
            filter_func: Function that takes a key string and returns True if it should be invalidated

        Returns:
            Number of keys invalidated

        Example:
            # Invalidate all playlist_videos keys that contain a specific playlist_id
            await cache_service.invalidate_by_filter(
                ["playlist_videos:*", "playlist_videos_by_date:*"],
                lambda key: f":playlist_id:{playlist_id}" in key
            )
        """
        from src.core.cache.client import get_redis_client
        from src.core.cache.operations import delete_cache

        client = await get_redis_client()
        invalidated_count = 0

        for prefix_pattern in key_prefixes:
            try:
                async for key in client.scan_iter(match=prefix_pattern):
                    # Apply filter function to determine if this key should be invalidated
                    if filter_func(key):
                        result = await delete_cache(key)
                        if result:
                            invalidated_count += 1
                            logger.debug(f"Invalidated cache key: {key}")
            except Exception as e:
                logger.error(f"Error invalidating cache pattern {prefix_pattern}: {e}")

        if invalidated_count > 0:
            logger.info(f"Invalidated {invalidated_count} cache entries")
        else:
            logger.warning("No cache entries found to invalidate")

        return invalidated_count

    async def flush_all(self) -> int:
        """
        Flush all cache entries from Redis.

        Returns:
            Number of keys deleted

        Warning:
            This will delete ALL keys in the current Redis database.
            Use with caution!
        """
        from src.core.cache.client import get_redis_client

        client = await get_redis_client()
        count = 0

        try:
            # Get all keys
            keys = []
            async for key in client.scan_iter(match="*"):
                keys.append(key)

            if not keys:
                logger.info("No cache entries to flush")
                return 0

            # Delete all keys
            deleted = await client.delete(*keys)
            count = deleted if isinstance(deleted, int) else len(keys)

            logger.warning(f"Flushed all cache: deleted {count} keys")
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            raise

        return count