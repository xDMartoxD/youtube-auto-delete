"""
Unit tests for VideoFilterService.
"""

import pytest
from datetime import datetime, timezone

from src.domain.services.video_filter_service import VideoFilterService


class TestVideoFilterService:
    """Tests for VideoFilterService."""

    @pytest.fixture
    def service(self):
        """Create VideoFilterService instance."""
        return VideoFilterService()

    @pytest.fixture
    def sample_item(self):
        """Sample playlist item."""
        return {
            "id": "item1",
            "snippet": {
                "title": "Test Video",
                "publishedAt": "2020-06-15T12:00:00Z",
            }
        }

    def test_filter_by_date_range_no_dates_returns_all(self, service, sample_item):
        """Test that filtering with no dates returns all items."""
        # Arrange
        items = [sample_item]

        # Act
        result = service.filter_by_date_range(items, None, None)

        # Assert
        assert result == items

    def test_filter_by_date_range_with_valid_range(self, service, sample_item):
        """Test filtering with valid date range."""
        # Arrange
        items = [sample_item]
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)

        # Act
        result = service.filter_by_date_range(items, date_from, date_to)

        # Assert
        assert len(result) == 1
        assert result[0] == sample_item

    def test_filter_by_date_range_excludes_out_of_range(self, service, sample_item):
        """Test that items outside date range are excluded."""
        # Arrange
        item_out_of_range = {
            "id": "item2",
            "snippet": {
                "title": "Old Video",
                "publishedAt": "2019-06-15T12:00:00Z",
            }
        }
        items = [sample_item, item_out_of_range]
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)

        # Act
        result = service.filter_by_date_range(items, date_from, date_to)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "item1"

    def test_filter_by_date_range_invalid_range_returns_empty(self, service, sample_item):
        """Test that invalid date range returns empty list."""
        # Arrange
        items = [sample_item]
        date_from = datetime(2020, 12, 31, tzinfo=timezone.utc)
        date_to = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Invalid: to < from

        # Act
        result = service.filter_by_date_range(items, date_from, date_to)

        # Assert
        assert result == []

    def test_filter_by_date_range_only_date_from(self, service, sample_item):
        """Test filtering with only date_from."""
        # Arrange
        item_before = {
            "id": "item2",
            "snippet": {
                "title": "Old Video",
                "publishedAt": "2019-06-15T12:00:00Z",
            }
        }
        items = [sample_item, item_before]
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)

        # Act
        result = service.filter_by_date_range(items, date_from, None)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "item1"

    def test_filter_by_date_range_only_date_to(self, service, sample_item):
        """Test filtering with only date_to."""
        # Arrange
        item_after = {
            "id": "item2",
            "snippet": {
                "title": "Future Video",
                "publishedAt": "2021-06-15T12:00:00Z",
            }
        }
        items = [sample_item, item_after]
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)

        # Act
        result = service.filter_by_date_range(items, None, date_to)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "item1"

    def test_should_include_item_no_published_at_excludes(self, service):
        """Test that items without publishedAt are excluded."""
        # Arrange
        item = {
            "id": "item1",
            "snippet": {}
        }
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)

        # Act
        result = service.should_include_item(item, None, date_from, date_to)

        # Assert
        assert result is False

    def test_should_include_item_invalid_date_format_excludes(self, service):
        """Test that items with invalid date format are excluded."""
        # Arrange
        item = {
            "id": "item1",
            "snippet": {
                "publishedAt": "invalid-date"
            }
        }
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)

        # Act
        result = service.should_include_item(item, None, date_from, date_to)

        # Assert
        assert result is False

    def test_should_include_item_no_snippet_excludes(self, service):
        """Test that items without snippet are excluded."""
        # Arrange
        item = {
            "id": "item1"
        }
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc)

        # Act
        result = service.should_include_item(item, None, date_from, date_to)

        # Assert
        assert result is False

    def test_should_include_item_with_date_range_object(self, service, sample_item):
        """Test should_include_item with DateRange object."""
        # Arrange
        from src.domain.value_objects.date_range import DateRange
        date_range = DateRange(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc)
        )

        # Act
        result = service.should_include_item(sample_item, date_range, None, None)

        # Assert
        assert result is True

