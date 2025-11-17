"""
Unit tests for DateRange value object.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.domain.value_objects.date_range import DateRange


class TestDateRange:
    """Tests for DateRange value object."""

    def test_create_valid_date_range(self):
        """Test creating a valid date range."""
        # Arrange
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)

        # Act
        date_range = DateRange(date_from=date_from, date_to=date_to)

        # Assert
        assert date_range.date_from == date_from
        assert date_range.date_to == date_to

    def test_create_date_range_with_naive_datetimes(self):
        """Test that naive datetimes are converted to UTC."""
        # Arrange
        date_from = datetime(2020, 1, 1)
        date_to = datetime(2020, 12, 31)

        # Act
        date_range = DateRange(date_from=date_from, date_to=date_to)

        # Assert
        assert date_range.date_from.tzinfo == timezone.utc
        assert date_range.date_to.tzinfo == timezone.utc

    def test_create_date_range_invalid_order_raises_error(self):
        """Test that date_to < date_from raises ValueError."""
        # Arrange
        date_from = datetime(2020, 12, 31, tzinfo=timezone.utc)
        date_to = datetime(2020, 1, 1, tzinfo=timezone.utc)

        # Act & Assert
        with pytest.raises(ValueError, match="date_to must be >= date_from"):
            DateRange(date_from=date_from, date_to=date_to)

    def test_create_date_range_before_youtube_launch_raises_error(self):
        """Test that date_from before YouTube launch raises ValueError."""
        # Arrange
        date_from = datetime(2005, 4, 19, tzinfo=timezone.utc)
        date_to = datetime(2020, 1, 1, tzinfo=timezone.utc)

        # Act & Assert
        with pytest.raises(ValueError, match="date_from must be >= 2005-04-20"):
            DateRange(date_from=date_from, date_to=date_to)

    def test_create_date_range_future_date_raises_error(self):
        """Test that date_to in the future raises ValueError."""
        # Arrange
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime.now(timezone.utc) + timedelta(days=1)

        # Act & Assert
        with pytest.raises(ValueError, match="date_to must be <= current time"):
            DateRange(date_from=date_from, date_to=date_to)

    def test_contains_date_within_range(self):
        """Test contains returns True for date within range."""
        # Arrange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc)
        )
        test_date = datetime(2020, 6, 15, tzinfo=timezone.utc)

        # Act
        result = date_range.contains(test_date)

        # Assert
        assert result is True

    def test_contains_date_before_range(self):
        """Test contains returns False for date before range."""
        # Arrange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc)
        )
        test_date = datetime(2019, 12, 31, tzinfo=timezone.utc)

        # Act
        result = date_range.contains(test_date)

        # Assert
        assert result is False

    def test_contains_date_after_range(self):
        """Test contains returns False for date after range."""
        # Arrange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc)
        )
        test_date = datetime(2021, 1, 1, tzinfo=timezone.utc)

        # Act
        result = date_range.contains(test_date)

        # Assert
        assert result is False

    def test_contains_date_at_boundaries(self):
        """Test contains returns True for dates at boundaries."""
        # Arrange
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)
        date_range = DateRange(date_from=date_from, date_to=date_to)

        # Act & Assert
        assert date_range.contains(date_from) is True
        assert date_range.contains(date_to) is True

    def test_contains_naive_datetime(self):
        """Test contains converts naive datetime to UTC."""
        # Arrange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc)
        )
        naive_date = datetime(2020, 6, 15)

        # Act
        result = date_range.contains(naive_date)

        # Assert
        assert result is True

    def test_duration_days(self):
        """Test duration_days calculates correctly."""
        # Arrange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 1, 31, tzinfo=timezone.utc)
        )

        # Act
        duration = date_range.duration_days()

        # Assert
        assert duration == 30

    def test_is_valid(self):
        """Test is_valid returns True for valid range."""
        # Arrange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc)
        )

        # Act
        result = date_range.is_valid()

        # Assert
        assert result is True

    def test_is_immutable(self):
        """Test that DateRange is immutable (frozen dataclass)."""
        # Arrange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc)
        )

        # Act & Assert
        with pytest.raises(Exception):  # FrozenInstanceError
            date_range.date_from = datetime(2021, 1, 1, tzinfo=timezone.utc)

