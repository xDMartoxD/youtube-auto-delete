"""JSON serialization for cache operations."""

import json
import logging
from decimal import Decimal
from typing import Any

from src.core.cache.operations import get_cache, set_cache

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal types from DynamoDB."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            # Convert Decimal to int if it's a whole number, otherwise to float
            if o % 1 == 0:
                return int(o)
            return float(o)
        return super().default(o)


async def get_json_cache(key: str) -> dict | None:
    """
    Get JSON value from cache.

    Args:
        key: Cache key

    Returns:
        Cached value as dict, or None if not found or invalid JSON
    """
    cached = await get_cache(key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for key {key}")
            return None
    return None


async def set_json_cache(key: str, value: dict, expire: int | None = None) -> bool:
    """
    Set JSON value in cache.

    Args:
        key: Cache key
        value: Value to cache (must be JSON-serializable dict)
        expire: Expiration time in seconds (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        json_str = json.dumps(value, cls=DecimalEncoder)
        return await set_cache(key, json_str, expire)
    except (TypeError, ValueError) as e:
        logger.warning(f"Error serializing value for cache key {key}: {e}")
        return False
