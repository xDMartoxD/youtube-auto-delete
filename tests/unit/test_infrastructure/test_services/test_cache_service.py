"""
Unit tests for CacheService.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.infrastructure.services.cache_service import CacheService


class TestCacheService:
    """Tests for CacheService."""

    @pytest.fixture
    def service(self):
        """Create CacheService instance."""
        return CacheService()

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, service):
        """Test getting value from cache when it exists."""
        # Arrange
        cached_data = {"key": "value"}
        with patch("src.infrastructure.services.cache_service.get_json_cache", return_value=cached_data):
            with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                # Act
                result = await service.get("test_prefix", arg1="value1")

                # Assert
                assert result == cached_data

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, service):
        """Test getting value from cache when it doesn't exist."""
        # Arrange
        with patch("src.infrastructure.services.cache_service.get_json_cache", return_value=None):
            with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                # Act
                result = await service.get("test_prefix", arg1="value1")

                # Assert
                assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, service):
        """Test setting value in cache successfully."""
        # Arrange
        value = {"key": "value"}
        with patch("src.infrastructure.services.cache_service.set_json_cache", return_value=True):
            with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                # Act
                result = await service.set("test_prefix", value, expire=3600, arg1="value1")

                # Assert
                assert result is True

    @pytest.mark.asyncio
    async def test_set_failure(self, service):
        """Test setting value in cache when it fails."""
        # Arrange
        value = {"key": "value"}
        with patch("src.infrastructure.services.cache_service.set_json_cache", return_value=False):
            with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                # Act
                result = await service.set("test_prefix", value, expire=3600, arg1="value1")

                # Assert
                assert result is False

    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self, service):
        """Test get_or_set when cache hit."""
        # Arrange
        cached_data = {"key": "value"}
        fetch_func = AsyncMock()
        
        with patch("src.infrastructure.services.cache_service.get_json_cache", return_value=cached_data):
            with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                # Act
                result = await service.get_or_set("test_prefix", fetch_func, expire=3600, arg1="value1")

                # Assert
                assert result == cached_data
                fetch_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss(self, service):
        """Test get_or_set when cache miss."""
        # Arrange
        fetch_result = {"key": "value"}
        fetch_func = AsyncMock(return_value=fetch_result)
        
        with patch("src.infrastructure.services.cache_service.get_json_cache", return_value=None):
            with patch("src.infrastructure.services.cache_service.set_json_cache", return_value=True):
                with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                    # Act
                    result = await service.get_or_set("test_prefix", fetch_func, expire=3600, arg1="value1")

                    # Assert
                    assert result == fetch_result
                    fetch_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_set_with_pydantic_model(self, service):
        """Test get_or_set with Pydantic model."""
        # Arrange
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            key: str
        
        fetch_result = TestModel(key="value")
        fetch_func = AsyncMock(return_value=fetch_result)
        
        with patch("src.infrastructure.services.cache_service.get_json_cache", return_value=None):
            with patch("src.infrastructure.services.cache_service.set_json_cache", return_value=True):
                with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                    # Act
                    result = await service.get_or_set("test_prefix", fetch_func, expire=3600)

                    # Assert
                    assert isinstance(result, dict)
                    assert result["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_or_set_with_non_dict_non_model(self, service):
        """Test get_or_set with non-dict, non-model value."""
        # Arrange
        fetch_result = "string_value"  # Not dict or model
        fetch_func = AsyncMock(return_value=fetch_result)
        
        with patch("src.infrastructure.services.cache_service.get_json_cache", return_value=None):
            with patch("src.infrastructure.services.cache_service.cache_key", return_value="test_key"):
                # Act
                result = await service.get_or_set("test_prefix", fetch_func, expire=3600)

                # Assert
                assert result == fetch_result  # Should return as-is

