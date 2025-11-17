"""
Unit tests for SuggestionService.
"""

import pytest

from src.domain.services.suggestion_service import SuggestionService
from src.domain.entities.suggestion import Suggestion
from src.domain.exceptions.domain_exceptions import SuggestionNotFoundDomainException


class TestSuggestionService:
    """Tests for SuggestionService."""

    @pytest.fixture
    def service(self):
        """Create SuggestionService instance."""
        return SuggestionService()

    @pytest.fixture
    def suggestion(self):
        """Create a suggestion."""
        return Suggestion.create("Test Title", "Test Description")

    def test_validate_suggestion_exists_with_valid_suggestion(self, service, suggestion):
        """Test validate_suggestion_exists returns suggestion when it exists."""
        # Act
        result = service.validate_suggestion_exists(suggestion)

        # Assert
        assert result == suggestion

    def test_validate_suggestion_exists_with_none_raises_error(self, service):
        """Test validate_suggestion_exists raises exception when suggestion is None."""
        # Act & Assert
        with pytest.raises(SuggestionNotFoundDomainException, match="Suggestion not found"):
            service.validate_suggestion_exists(None)

    def test_can_update_returns_true(self, service, suggestion):
        """Test can_update always returns True."""
        # Act
        result = service.can_update(suggestion)

        # Assert
        assert result is True

    def test_can_delete_returns_true(self, service, suggestion):
        """Test can_delete always returns True."""
        # Act
        result = service.can_delete(suggestion)

        # Assert
        assert result is True

