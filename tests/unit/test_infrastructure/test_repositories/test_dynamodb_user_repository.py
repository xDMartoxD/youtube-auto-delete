"""
Unit tests for DynamoDBUserRepository.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.repositories.dynamodb_user_repository import DynamoDBUserRepository
from src.domain.aggregates.user_aggregate import UserAggregate
from src.infrastructure.persistence.models.token_model import TokenModel
from src.infrastructure.persistence.dynamodb.types import Types
from botocore.exceptions import ClientError


class TestDynamoDBUserRepository:
    """Tests for DynamoDBUserRepository."""

    @pytest.fixture
    def repository(self):
        """Create DynamoDBUserRepository instance."""
        return DynamoDBUserRepository()

    @pytest.fixture
    def sample_token_model(self):
        """Create sample TokenModel."""
        return TokenModel(
            PK=f"{Types.USER.value}#test_user",
            SK=Types.TOKEN.value,
            type="token",
            provider="google",
            token_id="token123",
            access_token="access_token",
            refresh_token="refresh_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token_expires_in=86400,
            issued_at=1234567890,
            expires_at=1234571490,
            refresh_expires_at=1234654290,
            GSI2PK="gsi2pk",
            GSI2SK="gsi2sk",
            ttl=1234654290,
        )

    @pytest.mark.asyncio
    async def test_get_token_by_sub_success(self, repository, sample_token_model):
        """Test getting token by sub successfully."""
        # Arrange
        sub = "test_user"
        key = {"PK": f"{Types.USER.value}#{sub}", "SK": Types.TOKEN.value}
        item_data = sample_token_model.to_item()
        
        repository.get_item = AsyncMock(return_value=item_data)

        # Act
        result = await repository.get_token_by_sub(sub)

        # Assert
        assert result is not None
        assert result.PK == sample_token_model.PK
        repository.get_item.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_get_token_by_sub_not_found(self, repository):
        """Test getting token by sub when not found."""
        # Arrange
        sub = "non_existent"
        repository.get_item = AsyncMock(return_value=None)

        # Act
        result = await repository.get_token_by_sub(sub)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_insert_token_model_success(self, repository, sample_token_model):
        """Test inserting token model successfully."""
        # Arrange
        repository.insert = AsyncMock(return_value={})

        # Act
        await repository.insert_token_model(sample_token_model)

        # Assert
        repository.insert.assert_called_once_with(sample_token_model)

    @pytest.mark.asyncio
    async def test_find_by_id_success(self, repository, sample_token_model):
        """Test finding user by ID successfully."""
        # Arrange
        user_id = "test_user"
        repository.get_token_by_sub = AsyncMock(return_value=sample_token_model)

        # Act
        result = await repository.find_by_id(user_id)

        # Assert
        assert result is not None
        assert isinstance(result, UserAggregate)
        repository.get_token_by_sub.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository):
        """Test finding user by ID when not found."""
        # Arrange
        user_id = "non_existent"
        repository.get_token_by_sub = AsyncMock(return_value=None)

        # Act
        result = await repository.find_by_id(user_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_email_returns_none(self, repository):
        """Test that find_by_email returns None (not fully supported)."""
        # Arrange
        email = "test@example.com"

        # Act
        result = await repository.find_by_email(email)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_success(self, repository):
        """Test deleting user successfully."""
        # Arrange
        user_id = "test_user"
        repository.delete_item = AsyncMock(return_value={})

        # Act
        await repository.delete(user_id)

        # Assert
        key = {"PK": f"{Types.USER.value}#{user_id}", "SK": Types.TOKEN.value}
        repository.delete_item.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_update_token_success(self, repository):
        """Test updating token successfully."""
        # Arrange
        sub = "test_user"
        token_data = {
            "access_token": "new_access_token",
            "expires_at": 1234567890,
        }
        repository.update_item = AsyncMock(return_value={})

        # Act
        await repository.update_token(sub, token_data)

        # Assert
        key = {"PK": f"{Types.USER.value}#{sub}", "SK": Types.TOKEN.value}
        repository.update_item.assert_called_once()
        call_kwargs = repository.update_item.call_args[1]
        assert call_kwargs["key"] == key
        assert "UpdateExpression" in call_kwargs
        assert "ExpressionAttributeValues" in call_kwargs

    @pytest.mark.asyncio
    async def test_save_with_existing_token(self, repository):
        """Test saving user with existing token."""
        # Arrange
        user = UserAggregate.create("test_user", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )
        
        existing_token = MagicMock(spec=TokenModel)
        repository.get_token_by_sub = AsyncMock(return_value=existing_token)
        repository.insert = AsyncMock(return_value={})

        # Act
        await repository.save(user)

        # Assert
        repository.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_without_session_raises_error(self, repository):
        """Test that saving user without session raises ValueError."""
        # Arrange
        user = UserAggregate.create("test_user", "test@example.com")

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot save user without session"):
            await repository.save(user)

    @pytest.mark.asyncio
    async def test_save_without_existing_token_raises_error(self, repository):
        """Test that saving user without existing token raises ValueError."""
        # Arrange
        user = UserAggregate.create("test_user", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )
        
        repository.get_token_by_sub = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot save user without existing TokenModel"):
            await repository.save(user)

