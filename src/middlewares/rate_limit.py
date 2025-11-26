"""Rate limiting middleware using Redis."""

import time
import logging
from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

import redis.asyncio as aioredis

from src.core.config import config
from src.core.cache import get_redis_client

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting using Redis."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.requests_per_minute = config.rate_limit_per_minute
        self.requests_per_hour = config.rate_limit_per_hour

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits before processing request."""
        if not self.enabled or not config.rate_limit_enabled:
            return await call_next(request)

        # Skip rate limiting for health checks and OPTIONS requests (CORS preflight)
        if (
            request.url.path.startswith("/v1/health")
            or request.url.path.startswith("/api/health")  # Legacy support
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()

        try:
            redis_client = await get_redis_client()

            # Check per-minute limit
            minute_key = f"rate_limit:minute:{client_ip}"
            minute_count = await redis_client.get(minute_key)
            if minute_count and int(minute_count) >= self.requests_per_minute:
                logger.warning(
                    f"Rate limit exceeded (per minute) for IP: {client_ip}",
                    extra={"ip": client_ip, "limit": self.requests_per_minute},
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": "60"},
                )

            # Check per-hour limit
            hour_key = f"rate_limit:hour:{client_ip}"
            hour_count = await redis_client.get(hour_key)
            if hour_count and int(hour_count) >= self.requests_per_hour:
                logger.warning(
                    f"Rate limit exceeded (per hour) for IP: {client_ip}",
                    extra={"ip": client_ip, "limit": self.requests_per_hour},
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": "3600"},
                )

            # Increment counters using sliding window
            current_minute = int(time.time() // 60)
            current_hour = int(time.time() // 3600)

            # Increment minute counter (sliding window)
            minute_key_with_time = f"{minute_key}:{current_minute}"
            minute_count = await redis_client.incr(minute_key_with_time)
            await redis_client.expire(minute_key_with_time, 60)

            # Update the main minute key for checking (use max of current window)
            existing_minute = await redis_client.get(minute_key)
            if not existing_minute or minute_count > int(existing_minute):
                await redis_client.set(minute_key, minute_count, ex=60)

            # Increment hour counter (sliding window)
            hour_key_with_time = f"{hour_key}:{current_hour}"
            hour_count = await redis_client.incr(hour_key_with_time)
            await redis_client.expire(hour_key_with_time, 3600)

            # Update the main hour key for checking (use max of current window)
            existing_hour = await redis_client.get(hour_key)
            if not existing_hour or hour_count > int(existing_hour):
                await redis_client.set(hour_key, hour_count, ex=3600)

        except HTTPException:
            raise
        except (
            aioredis.RedisError,
            aioredis.ConnectionError,
            aioredis.TimeoutError,
        ) as e:
            # If Redis is unavailable, log and allow request (fail open)
            logger.warning(f"Redis error in rate limiting (allowing request): {e}")
            # In production, you might want to fail closed instead
        except Exception as e:
            # If Redis is unavailable, log and allow request (fail open)
            logger.error(
                f"Unexpected error in rate limiting (allowing request): {e}",
                exc_info=True,
            )
            # In production, you might want to fail closed instead

        return await call_next(request)
