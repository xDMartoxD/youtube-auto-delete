"""
Unit tests for SuggestionsService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.services.suggestions_service import SuggestionsService
from src.domain.entities.suggestion import Suggestion
from src.domain.exceptions.domain_exceptions import SuggestionNotFoundDomainException
from src.core.exceptions import SuggestionNotFoundError
from src.schemas.suggestions import SuggestionCreate, SuggestionUpdate


class TestSuggestionsService:
    """Tests for SuggestionsService."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create SuggestionsService instance."""
        return SuggestionsService(suggestion_repo=mock_repository)

    @pytest.fixture
    def sample_suggestion(self):
        """Create sample suggestion."""
        return Suggestion.create("Test Title", "Test Description")

    @pytest.mark.asyncio
    async def test_create_suggestion_success(self, service, mock_repository):
        """Test creating a suggestion successfully."""
        # Arrange
        suggestion_data = SuggestionCreate(title="New Title", description="New Description")
        mock_repository.save = AsyncMock()

        # Act
        result = await service.create_suggestion(suggestion_data)

        # Assert
        assert result.id is not None
        assert result.title == "New Title"
        assert result.description == "New Description"
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_suggestion_success(self, service, mock_repository, sample_suggestion):
        """Test getting a suggestion successfully."""
        # Arrange
        suggestion_id = sample_suggestion.id
        mock_repository.find_by_id = AsyncMock(return_value=sample_suggestion)

        # Act
        result = await service.get_suggestion(suggestion_id)

        # Assert
        assert result.id == suggestion_id
        assert result.title == sample_suggestion.title
        mock_repository.find_by_id.assert_called_once_with(suggestion_id)

    @pytest.mark.asyncio
    async def test_get_suggestion_not_found(self, service, mock_repository):
        """Test getting a non-existent suggestion raises error."""
        # Arrange
        suggestion_id = "non_existent"
        mock_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(SuggestionNotFoundError):
            await service.get_suggestion(suggestion_id)

    @pytest.mark.asyncio
    async def test_get_all_suggestions(self, service, mock_repository, sample_suggestion):
        """Test getting all suggestions."""
        # Arrange
        suggestions = [sample_suggestion]
        mock_repository.find_all = AsyncMock(return_value=suggestions)

        # Act
        result = await service.get_all_suggestions()

        # Assert
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == sample_suggestion.id
        mock_repository.find_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_suggestion_success(self, service, mock_repository, sample_suggestion):
        """Test updating a suggestion successfully."""
        # Arrange
        suggestion_id = sample_suggestion.id
        update_data = SuggestionUpdate(title="Updated Title")
        mock_repository.find_by_id = AsyncMock(return_value=sample_suggestion)
        mock_repository.save = AsyncMock()

        # Act
        result = await service.update_suggestion(suggestion_id, update_data)

        # Assert
        assert result.title == "Updated Title"
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_suggestion_not_found(self, service, mock_repository):
        """Test updating non-existent suggestion raises error."""
        # Arrange
        suggestion_id = "non_existent"
        update_data = SuggestionUpdate(title="New Title")
        mock_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(SuggestionNotFoundError):
            await service.update_suggestion(suggestion_id, update_data)

    @pytest.mark.asyncio
    async def test_update_suggestion_cannot_update(self, service, mock_repository, sample_suggestion):
        """Test updating suggestion when it cannot be updated."""
        # Arrange
        suggestion_id = sample_suggestion.id
        update_data = SuggestionUpdate(title="New Title")
        mock_repository.find_by_id = AsyncMock(return_value=sample_suggestion)
        
        # Mock can_update to return False
        service.suggestion_service.can_update = MagicMock(return_value=False)

        # Act & Assert
        with pytest.raises(ValueError, match="Suggestion cannot be updated"):
            await service.update_suggestion(suggestion_id, update_data)

    @pytest.mark.asyncio
    async def test_delete_suggestion_success(self, service, mock_repository, sample_suggestion):
        """Test deleting a suggestion successfully."""
        # Arrange
        suggestion_id = sample_suggestion.id
        mock_repository.find_by_id = AsyncMock(return_value=sample_suggestion)
        mock_repository.delete = AsyncMock()

        # Act
        await service.delete_suggestion(suggestion_id)

        # Assert
        mock_repository.delete.assert_called_once_with(suggestion_id)

    @pytest.mark.asyncio
    async def test_delete_suggestion_not_found(self, service, mock_repository):
        """Test deleting non-existent suggestion raises error."""
        # Arrange
        suggestion_id = "non_existent"
        mock_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(SuggestionNotFoundError):
            await service.delete_suggestion(suggestion_id)

    @pytest.mark.asyncio
    async def test_delete_suggestion_cannot_delete(self, service, mock_repository, sample_suggestion):
        """Test deleting suggestion when it cannot be deleted."""
        # Arrange
        suggestion_id = sample_suggestion.id
        mock_repository.find_by_id = AsyncMock(return_value=sample_suggestion)
        
        # Mock can_delete to return False
        service.suggestion_service.can_delete = MagicMock(return_value=False)

        # Act & Assert
        with pytest.raises(ValueError, match="Suggestion cannot be deleted"):
            await service.delete_suggestion(suggestion_id)

