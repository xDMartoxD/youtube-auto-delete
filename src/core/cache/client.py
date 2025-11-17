"""Redis client connection management."""

import logging
import ssl

import redis.asyncio as aioredis

from src.core.config import config

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: aioredis.Redis | None = None

# SSL certificate requirements mapping
_SSL_CERT_REQS_MAP = {
    "none": ssl.CERT_NONE,
    "optional": ssl.CERT_OPTIONAL,
    "required": ssl.CERT_REQUIRED,
}


def _get_ssl_cert_requirement() -> int:
    """
    Get SSL certificate requirement value from config.

    Returns:
        SSL certificate requirement constant (CERT_NONE, CERT_OPTIONAL, or CERT_REQUIRED)
    """
    return _SSL_CERT_REQS_MAP.get(config.redis_ssl_cert_reqs, ssl.CERT_REQUIRED)


def _create_ssl_context() -> ssl.SSLContext:
    """Create SSL context for Redis TLS connection."""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = config.redis_ssl_cert_reqs != "none"
    # Type cast needed because verify_mode expects VerifyMode enum, not int
    ssl_context.verify_mode = ssl.VerifyMode(_get_ssl_cert_requirement())  # type: ignore[assignment]
    return ssl_context


def _get_connection_kwargs_from_url() -> dict:
    """Build connection kwargs from Redis URL."""
    redis_url = config.redis_url
    if not redis_url:
        raise ValueError("redis_url is required when using URL-based connection")
    use_tls = redis_url.startswith("rediss://")

    connection_kwargs = {
        "encoding": "utf-8",
        "decode_responses": True,
    }

    if use_tls or config.redis_use_tls:
        connection_kwargs["ssl_cert_reqs"] = _get_ssl_cert_requirement()
        connection_kwargs["ssl_check_hostname"] = config.redis_ssl_cert_reqs != "none"

    return connection_kwargs


def _get_connection_kwargs_from_host_port() -> dict:
    """Build connection kwargs from host/port configuration."""
    connection_kwargs = {
        "host": config.redis_host,
        "port": config.redis_port,
        "db": config.redis_db,
        "encoding": "utf-8",
        "decode_responses": True,
    }

    if config.redis_password:
        connection_kwargs["password"] = config.redis_password

    if config.redis_use_tls:
        ssl_context = _create_ssl_context()
        connection_kwargs["ssl"] = ssl_context
        connection_kwargs["ssl_cert_reqs"] = ssl_context.verify_mode

    return connection_kwargs


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
            connection_kwargs = _get_connection_kwargs_from_url()
            _redis_client = aioredis.from_url(config.redis_url, **connection_kwargs)
        else:
            connection_kwargs = _get_connection_kwargs_from_host_port()
            _redis_client = aioredis.Redis(**connection_kwargs)

    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
