"""
Tests unitarios para configuración de ElastiCache.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import ssl

from src.core.cache import get_redis_client, close_redis_client
from src.core.config import config


class TestElastiCacheConfiguration:
    """Tests para configuración de ElastiCache."""

    @pytest.fixture(autouse=True)
    def reset_redis_client(self):
        """Reset Redis client before each test."""
        from src.core.cache import _redis_client
        global _redis_client
        _redis_client = None
        yield
        # Cleanup after test
        _redis_client = None

    @pytest.mark.asyncio
    async def test_elasticache_with_tls_url(self):
        """Test conexión a ElastiCache usando URL con TLS (rediss://)."""
        with patch("src.core.cache.config") as mock_config, patch(
            "redis.asyncio.from_url"
        ) as mock_from_url:
            mock_config.redis_url = "rediss://:password@elasticache-endpoint.cache.amazonaws.com:6379"
            mock_config.redis_use_tls = False
            mock_config.redis_ssl_cert_reqs = "required"

            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            # Act
            client = await get_redis_client()

            # Assert
            assert client is not None
            mock_from_url.assert_called_once()
            call_kwargs = mock_from_url.call_args[1]
            assert "ssl" in call_kwargs
            assert call_kwargs["ssl_cert_reqs"] == ssl.CERT_REQUIRED

    @pytest.mark.asyncio
    async def test_elasticache_without_tls_url(self):
        """Test conexión a ElastiCache usando URL sin TLS (redis://)."""
        with patch("src.core.cache.config") as mock_config, patch(
            "redis.asyncio.from_url"
        ) as mock_from_url:
            mock_config.redis_url = "redis://elasticache-endpoint.cache.amazonaws.com:6379"
            mock_config.redis_use_tls = False

            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            # Act
            client = await get_redis_client()

            # Assert
            assert client is not None
            mock_from_url.assert_called_once()
            call_kwargs = mock_from_url.call_args[1]
            assert "ssl" not in call_kwargs

    @pytest.mark.asyncio
    async def test_elasticache_with_host_port_tls(self):
        """Test conexión a ElastiCache usando host/port con TLS."""
        with patch("src.core.cache.config") as mock_config, patch(
            "redis.asyncio.Redis"
        ) as mock_redis:
            mock_config.redis_url = None
            mock_config.redis_host = "elasticache-endpoint.cache.amazonaws.com"
            mock_config.redis_port = 6379
            mock_config.redis_db = 0
            mock_config.redis_password = "test-password"
            mock_config.redis_use_tls = True
            mock_config.redis_ssl_cert_reqs = "required"

            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            # Act
            client = await get_redis_client()

            # Assert
            assert client is not None
            mock_redis.assert_called_once()
            call_kwargs = mock_redis.call_args[1]
            assert call_kwargs["host"] == "elasticache-endpoint.cache.amazonaws.com"
            assert call_kwargs["port"] == 6379
            assert call_kwargs["password"] == "test-password"
            assert "ssl" in call_kwargs
            assert call_kwargs["ssl_cert_reqs"] == ssl.CERT_REQUIRED

    @pytest.mark.asyncio
    async def test_local_redis_no_tls(self):
        """Test conexión a Redis local sin TLS."""
        with patch("src.core.cache.config") as mock_config, patch(
            "redis.asyncio.Redis"
        ) as mock_redis:
            mock_config.redis_url = None
            mock_config.redis_host = "localhost"
            mock_config.redis_port = 6379
            mock_config.redis_db = 0
            mock_config.redis_password = None
            mock_config.redis_use_tls = False

            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            # Act
            client = await get_redis_client()

            # Assert
            assert client is not None
            mock_redis.assert_called_once()
            call_kwargs = mock_redis.call_args[1]
            assert call_kwargs["host"] == "localhost"
            assert "ssl" not in call_kwargs
            assert "password" not in call_kwargs

    @pytest.mark.asyncio
    async def test_elasticache_ssl_cert_reqs_options(self):
        """Test diferentes opciones de SSL certificate requirements."""
        ssl_options = ["none", "optional", "required"]

        for ssl_option in ssl_options:
            with patch("src.core.cache.config") as mock_config, patch(
                "redis.asyncio.Redis"
            ) as mock_redis:
                mock_config.redis_url = None
                mock_config.redis_host = "elasticache-endpoint.cache.amazonaws.com"
                mock_config.redis_port = 6379
                mock_config.redis_use_tls = True
                mock_config.redis_ssl_cert_reqs = ssl_option

                mock_client = AsyncMock()
                mock_redis.return_value = mock_client

                # Reset client
                from src.core.cache import _redis_client
                global _redis_client
                _redis_client = None

                # Act
                client = await get_redis_client()

                # Assert
                assert client is not None
                call_kwargs = mock_redis.call_args[1]
                assert "ssl" in call_kwargs

                # Verify SSL context configuration
                ssl_context = call_kwargs["ssl"]
                if ssl_option == "none":
                    assert ssl_context.check_hostname is False
                    assert ssl_context.verify_mode == ssl.CERT_NONE
                elif ssl_option == "optional":
                    assert ssl_context.verify_mode == ssl.CERT_OPTIONAL
                else:  # required
                    assert ssl_context.verify_mode == ssl.CERT_REQUIRED

    @pytest.mark.asyncio
    async def test_elasticache_url_with_password(self):
        """Test URL de ElastiCache con password en la URL."""
        with patch("src.core.cache.config") as mock_config, patch(
            "redis.asyncio.from_url"
        ) as mock_from_url:
            mock_config.redis_url = "rediss://:my-password@elasticache-endpoint.cache.amazonaws.com:6379"
            mock_config.redis_use_tls = False

            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            # Act
            client = await get_redis_client()

            # Assert
            assert client is not None
            mock_from_url.assert_called_once()
            # Verify URL is passed correctly
            assert "rediss://" in mock_from_url.call_args[0][0]

