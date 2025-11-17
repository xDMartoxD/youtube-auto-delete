"""Redis cache client and utilities."""

import json
import logging
import ssl
from typing import Any, Callable, TypeVar
from functools import wraps

import redis.asyncio as aioredis

from src.core.config import config

logger = logging.getLogger(__name__)

# Type variable for function return types
T = TypeVar("T")

# Global Redis client instance
_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis:
    """
    Get or create Redis client instance.
    Supports both local Redis and AWS ElastiCache.

    For ElastiCache:
    - Use redis_url with format: redis://[password@]endpoint:port
    - For TLS: rediss://[password@]endpoint:port (note the double 's')
    - Or set redis_use_tls=True and provide redis_host/redis_port
    """
    global _redis_client

    if _redis_client is None:
        if config.redis_url:
            # Parse URL to determine if TLS is needed
            use_tls = config.redis_url.startswith("rediss://")

            # Build connection kwargs
            connection_kwargs = {
                "encoding": "utf-8",
                "decode_responses": True,
            }

            # Add TLS configuration if needed
            # ElastiCache with in-transit encryption uses TLS
            # Note: from_url() handles SSL automatically for rediss:// URLs
            # But we can configure SSL parameters if needed
            if use_tls or config.redis_use_tls:
                # Configure certificate requirements
                # For ElastiCache, typically use 'required' or 'optional'
                cert_reqs_map = {
                    "none": ssl.CERT_NONE,
                    "optional": ssl.CERT_OPTIONAL,
                    "required": ssl.CERT_REQUIRED,
                }

                # from_url() accepts ssl_cert_reqs and ssl_check_hostname, not ssl context
                connection_kwargs["ssl_cert_reqs"] = cert_reqs_map.get(
                    config.redis_ssl_cert_reqs, ssl.CERT_REQUIRED
                )
                connection_kwargs["ssl_check_hostname"] = (
                    config.redis_ssl_cert_reqs != "none"
                )

            _redis_client = aioredis.from_url(config.redis_url, **connection_kwargs)
        else:
            # Build connection kwargs for host/port configuration
            connection_kwargs = {
                "host": config.redis_host,
                "port": config.redis_port,
                "db": config.redis_db,
                "encoding": "utf-8",
                "decode_responses": True,
            }

            if config.redis_password:
                connection_kwargs["password"] = config.redis_password

            # Add TLS configuration if needed
            if config.redis_use_tls:
                ssl_context = ssl.create_default_context()

                cert_reqs_map = {
                    "none": ssl.CERT_NONE,
                    "optional": ssl.CERT_OPTIONAL,
                    "required": ssl.CERT_REQUIRED,
                }
                ssl_context.check_hostname = config.redis_ssl_cert_reqs != "none"
                ssl_context.verify_mode = cert_reqs_map.get(
                    config.redis_ssl_cert_reqs, ssl.CERT_REQUIRED
                )

                connection_kwargs["ssl"] = ssl_context
                connection_kwargs["ssl_cert_reqs"] = ssl_context.verify_mode

            _redis_client = aioredis.Redis(**connection_kwargs)

    return _redis_client


async def close_redis_client():
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


async def get_cache(key: str) -> str | None:
    """Get value from cache by key."""
    try:
        client = await get_redis_client()
        return await client.get(key)
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
        return None


async def set_cache(key: str, value: str, expire: int | None = None) -> bool:
    """Set value in cache with optional expiration (in seconds)."""
    try:
        client = await get_redis_client()
        if expire:
            await client.setex(key, expire, value)
        else:
            await client.set(key, value)
        return True
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False


async def delete_cache(key: str) -> bool:
    """Delete key from cache."""
    try:
        client = await get_redis_client()
        await client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        return False


async def get_json_cache(key: str) -> dict | None:
    """Get JSON value from cache."""
    cached = await get_cache(key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for key {key}")
            return None
    return None


async def set_json_cache(key: str, value: dict, expire: int | None = None) -> bool:
    """Set JSON value in cache."""
    try:
        json_str = json.dumps(value)
        return await set_cache(key, json_str, expire)
    except (TypeError, ValueError) as e:
        logger.warning(f"Error serializing value for cache key {key}: {e}")
        return False


def cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from prefix and arguments."""
    parts = [prefix]
    if args:
        parts.extend(str(arg) for arg in args)
    if kwargs:
        parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)


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
