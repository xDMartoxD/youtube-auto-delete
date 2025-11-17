"""
Unit tests for API utilities.
"""

import pytest
from datetime import datetime, timezone

from src.api.utils import parse_date, get_pagination_params, get_playlist_video_query_params
from src.core.exceptions import InvalidDateRangeError


class TestAPIUtils:
    """Tests for API utility functions."""

    def test_parse_date_with_z_suffix(self):
        """Test parsing date with Z suffix."""
        # Arrange
        date_str = "2020-06-15T12:00:00Z"

        # Act
        result = parse_date(date_str)

        # Assert
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_parse_date_with_timezone_offset(self):
        """Test parsing date with timezone offset."""
        # Arrange
        date_str = "2020-06-15T12:00:00+00:00"

        # Act
        result = parse_date(date_str)

        # Assert
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_parse_date_without_timezone(self):
        """Test parsing date without timezone (assumes UTC)."""
        # Arrange
        date_str = "2020-06-15T12:00:00"

        # Act
        result = parse_date(date_str)

        # Assert
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_date_date_only(self):
        """Test parsing date-only string."""
        # Arrange
        date_str = "2020-06-15"

        # Act
        result = parse_date(date_str)

        # Assert
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_date_none(self):
        """Test parsing None returns None."""
        # Act
        result = parse_date(None)

        # Assert
        assert result is None

    def test_parse_date_empty_string(self):
        """Test parsing empty string returns None."""
        # Act
        result = parse_date("")

        # Assert
        assert result is None

    def test_parse_date_invalid_format_raises_error(self):
        """Test that invalid date format raises InvalidDateRangeError."""
        # Arrange
        invalid_date = "not-a-date"

        # Act & Assert
        with pytest.raises(InvalidDateRangeError):
            parse_date(invalid_date)

    def test_get_pagination_params_defaults(self):
        """Test get_pagination_params with default values."""
        # Act
        result = get_pagination_params()

        # Assert
        assert result.max_results == 25
        assert result.page_token is None

    def test_get_pagination_params_custom(self):
        """Test get_pagination_params with custom values."""
        # Act
        result = get_pagination_params(max_results=50, page_token="token123")

        # Assert
        assert result.max_results == 50
        assert result.page_token == "token123"

    def test_get_playlist_video_query_params_no_dates(self):
        """Test get_playlist_video_query_params without dates."""
        # Act
        result = get_playlist_video_query_params(max_results=25)

        # Assert
        assert result.max_results == 25
        assert result.date_from is None
        assert result.date_to is None

    def test_get_playlist_video_query_params_with_dates(self):
        """Test get_playlist_video_query_params with dates."""
        # Arrange
        date_from_str = "2020-01-01T00:00:00Z"
        date_to_str = "2020-12-31T23:59:59Z"

        # Act
        result = get_playlist_video_query_params(
            max_results=25,
            date_from=date_from_str,
            date_to=date_to_str
        )

        # Assert
        assert result.max_results == 25
        assert result.date_from is not None
        assert result.date_to is not None
        assert isinstance(result.date_from, datetime)
        assert isinstance(result.date_to, datetime)

    def test_get_playlist_video_query_params_invalid_date(self):
        """Test get_playlist_video_query_params with invalid date."""
        # Arrange
        invalid_date = "not-a-date"

        # Act & Assert
        with pytest.raises(InvalidDateRangeError):
            get_playlist_video_query_params(date_from=invalid_date)

