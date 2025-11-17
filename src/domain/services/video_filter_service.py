"""Domain service for video filtering business rules."""

from datetime import datetime, timezone
from typing import Any

from src.domain.value_objects.date_range import DateRange


class VideoFilterService:
    """Domain service - contains ONLY business logic for video filtering."""

    def filter_by_date_range(
        self,
        items: list[dict[str, Any]],
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[dict[str, Any]]:
        """
        Filters playlist items by date range.
        Filters by date added to playlist (snippet.publishedAt).

        Business rule: If an item has no publication date, exclude it.
        """
        if not date_from and not date_to:
            return items

        # Create DateRange value object if both dates are present
        date_range = None
        if date_from and date_to:
            try:
                date_range = DateRange(date_from=date_from, date_to=date_to)
            except ValueError:
                # If range is invalid, return empty list
                return []

        filtered_items = []

        for item in items:
            if self.should_include_item(item, date_range, date_from, date_to):
                filtered_items.append(item)

        return filtered_items

    def should_include_item(
        self,
        item: dict[str, Any],
        date_range: DateRange | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> bool:
        """
        Determines if an item should be included based on date range.
        Business rule: If there's no date filter, always include.
        """
        if not date_from and not date_to:
            return True

        snippet = item.get("snippet", {})
        published_at_str = snippet.get("publishedAt")

        if not published_at_str:
            # Business rule: If no publication date, exclude
            return False

        try:
            published_at = datetime.fromisoformat(
                published_at_str.replace("Z", "+00:00")
            )
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            # If date cannot be parsed, exclude
            return False

        # Use DateRange if available, otherwise validate manually
        if date_range:
            return date_range.contains(published_at)

        # Manual validation if no complete DateRange
        if date_from:
            date_from_utc = date_from
            if date_from_utc.tzinfo is None:
                date_from_utc = date_from_utc.replace(tzinfo=timezone.utc)
            if published_at < date_from_utc:
                return False

        if date_to:
            date_to_utc = date_to
            if date_to_utc.tzinfo is None:
                date_to_utc = date_to_utc.replace(tzinfo=timezone.utc)
            if published_at > date_to_utc:
                return False

        return True

