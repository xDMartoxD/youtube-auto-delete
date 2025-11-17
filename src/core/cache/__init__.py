"""
Cache module - Redis caching utilities.

This module provides a clean interface for Redis caching operations,
divided into focused submodules:
- client: Redis client connection management
- operations: Basic string-based cache operations
- serialization: JSON serialization for cache
- utils: Cache key generation utilities
- decorators: Function result caching decorators
- invalidation: Cache invalidation strategies
"""

# Client management
from src.core.cache.client import close_redis_client, get_redis_client

# Basic operations
from src.core.cache.operations import delete_cache, get_cache, set_cache

# JSON serialization
from src.core.cache.serialization import get_json_cache, set_json_cache

# Utilities
from src.core.cache.utils import cache_key

# Decorators
from src.core.cache.decorators import cached

# Invalidation
from src.core.cache.invalidation import (
    CacheInvalidationStrategy,
    PrefixInvalidationStrategy,
    PatternInvalidationStrategy,
    invalidate_cache,
)

__all__ = [
    # Client
    "get_redis_client",
    "close_redis_client",
    # Operations
    "get_cache",
    "set_cache",
    "delete_cache",
    # Serialization
    "get_json_cache",
    "set_json_cache",
    # Utilities
    "cache_key",
    # Decorators
    "cached",
    # Invalidation
    "CacheInvalidationStrategy",
    "PrefixInvalidationStrategy",
    "PatternInvalidationStrategy",
    "invalidate_cache",
]

