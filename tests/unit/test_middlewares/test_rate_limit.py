"""
Unit tests for RateLimitMiddleware.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, HTTPException, status
from starlette.responses import Response

from src.middlewares.rate_limit import RateLimitMiddleware
from src.core.config import config


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""
        return MagicMock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Create RateLimitMiddleware instance."""
        return RateLimitMiddleware(mock_app, enabled=True)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function."""
        async def call_next(request):
            return Response(content="OK", status_code=200)
        return call_next

    @pytest.mark.asyncio
    async def test_middleware_disabled_skips_rate_limiting(self, mock_app, mock_request, mock_call_next):
        """Test that middleware skips rate limiting when disabled."""
        # Arrange
        middleware = RateLimitMiddleware(mock_app, enabled=False)

        # Act
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_skips_health_checks(self, mock_app, mock_request, mock_call_next):
        """Test that middleware skips rate limiting for health checks."""
        # Arrange
        mock_request.url.path = "/api/health"
        middleware = RateLimitMiddleware(mock_app, enabled=True)

        # Act
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_allows_request_under_limit(self, middleware, mock_request, mock_call_next):
        """Test that middleware allows requests under the limit."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No existing count
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.set = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("src.middlewares.rate_limit.get_redis_client", return_value=mock_redis):
            # Act
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Assert
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_blocks_request_over_minute_limit(self, middleware, mock_request, mock_call_next):
        """Test that middleware blocks requests over per-minute limit."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=str(middleware.requests_per_minute))  # At limit
        mock_redis.incr = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("src.middlewares.rate_limit.get_redis_client", return_value=mock_redis):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(mock_request, mock_call_next)

            assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_middleware_blocks_request_over_hour_limit(self, middleware, mock_request, mock_call_next):
        """Test that middleware blocks requests over per-hour limit."""
        # Arrange
        mock_redis = AsyncMock()
        # Minute check passes
        mock_redis.get = AsyncMock(side_effect=[
            None,  # Minute check - no limit
            str(middleware.requests_per_hour)  # Hour check - at limit
        ])
        mock_redis.incr = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("src.middlewares.rate_limit.get_redis_client", return_value=mock_redis):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(mock_request, mock_call_next)

            assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_middleware_uses_x_forwarded_for_header(self, middleware, mock_request, mock_call_next):
        """Test that middleware uses X-Forwarded-For header when present."""
        # Arrange
        mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.set = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("src.middlewares.rate_limit.get_redis_client", return_value=mock_redis):
            # Act
            await middleware.dispatch(mock_request, mock_call_next)

            # Assert - Check that IP from header was used
            calls = [str(call) for call in mock_redis.get.call_args_list]
            assert any("192.168.1.1" in str(call) for call in mock_redis.get.call_args_list)

    @pytest.mark.asyncio
    async def test_middleware_handles_redis_error_gracefully(self, middleware, mock_request, mock_call_next):
        """Test that middleware handles Redis errors gracefully (fail open)."""
        # Arrange
        with patch("src.middlewares.rate_limit.get_redis_client", side_effect=Exception("Redis error")):
            # Act
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Assert - Should allow request (fail open)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_increments_counters(self, middleware, mock_request, mock_call_next):
        """Test that middleware increments counters correctly."""
        # Arrange
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.set = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("src.middlewares.rate_limit.get_redis_client", return_value=mock_redis):
            # Act
            await middleware.dispatch(mock_request, mock_call_next)

            # Assert
            assert mock_redis.incr.call_count >= 2  # Minute and hour counters
            assert mock_redis.set.call_count >= 2
            assert mock_redis.expire.call_count >= 2

