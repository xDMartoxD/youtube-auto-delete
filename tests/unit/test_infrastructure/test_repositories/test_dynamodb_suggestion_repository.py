"""
Unit tests for DynamoDBSuggestionRepository.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.repositories.dynamodb_suggestion_repository import DynamoDBSuggestionRepository
from src.domain.entities.suggestion import Suggestion
from src.infrastructure.persistence.models.suggestion_model import SuggestionModel
from src.infrastructure.persistence.dynamodb.types import Types
from botocore.exceptions import ClientError


class TestDynamoDBSuggestionRepository:
    """Tests for DynamoDBSuggestionRepository."""

    @pytest.fixture
    def repository(self):
        """Create DynamoDBSuggestionRepository instance."""
        return DynamoDBSuggestionRepository()

    @pytest.fixture
    def sample_suggestion(self):
        """Create sample Suggestion."""
        return Suggestion.create("Test Title", "Test Description")

    @pytest.mark.asyncio
    async def test_save_suggestion_success(self, repository, sample_suggestion):
        """Test saving a suggestion successfully."""
        # Arrange
        repository.insert = AsyncMock(return_value={})

        # Act
        await repository.save(sample_suggestion)

        # Assert
        repository.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_success(self, repository, sample_suggestion):
        """Test finding suggestion by ID successfully."""
        # Arrange
        suggestion_id = sample_suggestion.id
        key = {
            "PK": f"{Types.SUGGESTION.value}#{suggestion_id}",
            "SK": Types.SUGGESTION.value,
        }
        
        # Mock SuggestionModel.from_item
        suggestion_model = MagicMock(spec=SuggestionModel)
        with patch("src.infrastructure.repositories.dynamodb_suggestion_repository.SuggestionModel.from_item", return_value=suggestion_model):
            with patch("src.infrastructure.repositories.dynamodb_suggestion_repository.SuggestionMapper.to_domain", return_value=sample_suggestion):
                repository.get_item = AsyncMock(return_value={"id": suggestion_id})

                # Act
                result = await repository.find_by_id(suggestion_id)

                # Assert
                assert result is not None
                assert result.id == suggestion_id
                repository.get_item.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository):
        """Test finding suggestion by ID when not found."""
        # Arrange
        suggestion_id = "non_existent"
        repository.get_item = AsyncMock(return_value=None)

        # Act
        result = await repository.find_by_id(suggestion_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_success(self, repository):
        """Test finding all suggestions successfully."""
        # Arrange
        items = [
            {
                "PK": f"{Types.SUGGESTION.value}#id1",
                "SK": Types.SUGGESTION.value,
                "id": "id1",
                "title": "Title 1",
                "description": "Description 1",
                "created_at": 1234567890,
                "updated_at": 1234567890,
            },
            {
                "PK": f"{Types.SUGGESTION.value}#id2",
                "SK": Types.SUGGESTION.value,
                "id": "id2",
                "title": "Title 2",
                "description": "Description 2",
                "created_at": 1234567890,
                "updated_at": 1234567890,
            },
        ]

        with patch("src.infrastructure.repositories.dynamodb_suggestion_repository.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"Items": items}
            
            suggestion1 = Suggestion.create("Title 1", "Description 1")
            suggestion2 = Suggestion.create("Title 2", "Description 2")
            
            with patch("src.infrastructure.repositories.dynamodb_suggestion_repository.SuggestionModel.from_item") as mock_from_item:
                mock_from_item.side_effect = [
                    MagicMock(spec=SuggestionModel),
                    MagicMock(spec=SuggestionModel),
                ]
                with patch("src.infrastructure.repositories.dynamodb_suggestion_repository.SuggestionMapper.to_domain") as mock_to_domain:
                    mock_to_domain.side_effect = [suggestion1, suggestion2]

                    # Act
                    result = await repository.find_all()

                    # Assert
                    assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_all_handles_client_error(self, repository):
        """Test that find_all handles ClientError correctly."""
        # Arrange
        with patch("src.infrastructure.repositories.dynamodb_suggestion_repository.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}},
                "Scan"
            )

            # Act & Assert
            from src.core.exceptions import AwsFailedError
            with pytest.raises(AwsFailedError):
                await repository.find_all()

    @pytest.mark.asyncio
    async def test_find_all_handles_generic_error(self, repository):
        """Test that find_all handles generic errors gracefully."""
        # Arrange
        with patch("src.infrastructure.repositories.dynamodb_suggestion_repository.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Unexpected error")

            # Act
            result = await repository.find_all()

            # Assert - Should return empty list on generic error
            assert result == []

    @pytest.mark.asyncio
    async def test_delete_success(self, repository):
        """Test deleting a suggestion successfully."""
        # Arrange
        suggestion_id = "test_id"
        repository.delete_item = AsyncMock(return_value={})

        # Act
        await repository.delete(suggestion_id)

        # Assert
        key = {
            "PK": f"{Types.SUGGESTION.value}#{suggestion_id}",
            "SK": Types.SUGGESTION.value,
        }
        repository.delete_item.assert_called_once_with(key)

