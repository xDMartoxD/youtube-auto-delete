"""Cache invalidation strategies."""

import logging
from typing import Any

import redis.asyncio as aioredis

from src.core.cache.operations import delete_cache
from src.core.cache.utils import cache_key

logger = logging.getLogger(__name__)


class CacheInvalidationStrategy:
    """Base class for cache invalidation strategies."""

    async def invalidate(self, pattern: str, **kwargs: Any) -> int:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: Cache key pattern or prefix
            **kwargs: Additional parameters for pattern matching

        Returns:
            Number of keys invalidated
        """
        raise NotImplementedError


class PrefixInvalidationStrategy(CacheInvalidationStrategy):
    """
    Simple prefix-based invalidation strategy.
    
    Note: This is a simplified implementation. In production, you might want
    to use Redis SCAN with pattern matching for better performance with large caches.
    """

    async def invalidate(self, prefix: str, **kwargs: Any) -> int:
        """
        Invalidate all cache entries with the given prefix.

        Args:
            prefix: Cache key prefix to invalidate
            **kwargs: Additional parameters to build the key

        Returns:
            Number of keys invalidated
        """
        # Build the full key from prefix and kwargs
        key = cache_key(prefix, **kwargs)
        
        # Delete the specific key
        result = await delete_cache(key)
        if result:
            logger.info(f"Invalidated cache key: {key}")
            return 1
        return 0


class PatternInvalidationStrategy(CacheInvalidationStrategy):
    """
    Pattern-based invalidation using Redis SCAN.
    
    This is more efficient for invalidating multiple keys with a common pattern.
    """

    async def invalidate(self, pattern: str, **kwargs: Any) -> int:
        """
        Invalidate cache entries matching a pattern using Redis SCAN.

        Args:
            pattern: Redis key pattern (e.g., "user_playlists:*")
            **kwargs: Not used in this strategy, but kept for interface compatibility

        Returns:
            Number of keys invalidated
        """
        from src.core.cache.client import get_redis_client

        client = await get_redis_client()
        count = 0

        try:
            # Use SCAN to find all keys matching the pattern
            async for key in client.scan_iter(match=pattern):
                result = await delete_cache(key)
                if result:
                    count += 1
                    logger.debug(f"Invalidated cache key: {key}")

            if count > 0:
                logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")
        except (aioredis.RedisError, aioredis.ConnectionError, aioredis.TimeoutError) as e:
            logger.error(f"Redis error invalidating cache pattern {pattern}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error invalidating cache pattern {pattern}: {e}")
            raise

        return count


# Default invalidation strategy
default_invalidation_strategy = PrefixInvalidationStrategy()


async def invalidate_cache(prefix: str, strategy: CacheInvalidationStrategy | None = None, **kwargs: Any) -> int:
    """
    Convenience function to invalidate cache entries.

    Args:
        prefix: Cache key prefix to invalidate
        strategy: Invalidation strategy to use (default: PrefixInvalidationStrategy)
        **kwargs: Additional parameters for key building

    Returns:
        Number of keys invalidated
    """
    strategy = strategy or default_invalidation_strategy
    return await strategy.invalidate(prefix, **kwargs)

