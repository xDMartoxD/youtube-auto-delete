"""
Unit tests for Suggestion entity.
"""

import pytest
from datetime import datetime, timezone

from src.domain.entities.suggestion import Suggestion


class TestSuggestion:
    """Tests for Suggestion entity."""

    def test_create_suggestion(self):
        """Test creating a new suggestion."""
        # Act
        suggestion = Suggestion.create(
            title="Test Title",
            description="Test Description"
        )

        # Assert
        assert suggestion.id is not None
        assert len(suggestion.id) > 0
        assert suggestion.title == "Test Title"
        assert suggestion.description == "Test Description"
        assert isinstance(suggestion.created_at, datetime)
        assert isinstance(suggestion.updated_at, datetime)
        assert suggestion.created_at == suggestion.updated_at

    def test_create_suggestion_trims_whitespace(self):
        """Test that create trims whitespace from title and description."""
        # Act
        suggestion = Suggestion.create(
            title="  Test Title  ",
            description="  Test Description  "
        )

        # Assert
        assert suggestion.title == "Test Title"
        assert suggestion.description == "Test Description"

    def test_update_title_success(self):
        """Test updating title successfully."""
        # Arrange
        suggestion = Suggestion.create("Old Title", "Description")

        # Act
        suggestion.update_title("New Title")

        # Assert
        assert suggestion.title == "New Title"
        assert suggestion.updated_at > suggestion.created_at

    def test_update_title_empty_raises_error(self):
        """Test that updating with empty title raises ValueError."""
        # Arrange
        suggestion = Suggestion.create("Title", "Description")

        # Act & Assert
        with pytest.raises(ValueError, match="no puede estar vacío"):
            suggestion.update_title("")

    def test_update_title_whitespace_only_raises_error(self):
        """Test that updating with whitespace-only title raises ValueError."""
        # Arrange
        suggestion = Suggestion.create("Title", "Description")

        # Act & Assert
        with pytest.raises(ValueError, match="no puede estar vacío"):
            suggestion.update_title("   ")

    def test_update_title_too_long_raises_error(self):
        """Test that updating with title > 200 chars raises ValueError."""
        # Arrange
        suggestion = Suggestion.create("Title", "Description")
        long_title = "a" * 201

        # Act & Assert
        with pytest.raises(ValueError, match="no puede exceder 200 caracteres"):
            suggestion.update_title(long_title)

    def test_update_title_exactly_200_chars_success(self):
        """Test that updating with exactly 200 chars works."""
        # Arrange
        suggestion = Suggestion.create("Title", "Description")
        title_200 = "a" * 200

        # Act
        suggestion.update_title(title_200)

        # Assert
        assert suggestion.title == title_200

    def test_update_description_success(self):
        """Test updating description successfully."""
        # Arrange
        suggestion = Suggestion.create("Title", "Old Description")

        # Act
        suggestion.update_description("New Description")

        # Assert
        assert suggestion.description == "New Description"
        assert suggestion.updated_at > suggestion.created_at

    def test_update_description_empty_raises_error(self):
        """Test that updating with empty description raises ValueError."""
        # Arrange
        suggestion = Suggestion.create("Title", "Description")

        # Act & Assert
        with pytest.raises(ValueError, match="no puede estar vacía"):
            suggestion.update_description("")

    def test_update_description_too_long_raises_error(self):
        """Test that updating with description > 1000 chars raises ValueError."""
        # Arrange
        suggestion = Suggestion.create("Title", "Description")
        long_description = "a" * 1001

        # Act & Assert
        with pytest.raises(ValueError, match="no puede exceder 1000 caracteres"):
            suggestion.update_description(long_description)

    def test_update_both_fields(self):
        """Test updating both title and description."""
        # Arrange
        suggestion = Suggestion.create("Old Title", "Old Description")

        # Act
        suggestion.update(title="New Title", description="New Description")

        # Assert
        assert suggestion.title == "New Title"
        assert suggestion.description == "New Description"

    def test_update_only_title(self):
        """Test updating only title."""
        # Arrange
        suggestion = Suggestion.create("Old Title", "Description")
        original_description = suggestion.description

        # Act
        suggestion.update(title="New Title")

        # Assert
        assert suggestion.title == "New Title"
        assert suggestion.description == original_description

    def test_update_only_description(self):
        """Test updating only description."""
        # Arrange
        suggestion = Suggestion.create("Title", "Old Description")
        original_title = suggestion.title

        # Act
        suggestion.update(description="New Description")

        # Assert
        assert suggestion.title == original_title
        assert suggestion.description == "New Description"

    def test_update_none_does_nothing(self):
        """Test that update with None values does nothing."""
        # Arrange
        suggestion = Suggestion.create("Title", "Description")
        original_title = suggestion.title
        original_description = suggestion.description
        original_updated_at = suggestion.updated_at

        # Act
        suggestion.update(title=None, description=None)

        # Assert
        assert suggestion.title == original_title
        assert suggestion.description == original_description
        # updated_at should not change if nothing was updated
        assert suggestion.updated_at == original_updated_at

