"""Value object for date ranges."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class DateRange:
    """Value object representing a date range with business rules."""

    date_from: datetime
    date_to: datetime

    def __post_init__(self) -> None:
        """Validate date range."""
        # Ensure timezone-aware datetimes
        if self.date_from.tzinfo is None:
            object.__setattr__(
                self, "date_from", self.date_from.replace(tzinfo=timezone.utc)
            )
        if self.date_to.tzinfo is None:
            object.__setattr__(
                self, "date_to", self.date_to.replace(tzinfo=timezone.utc)
            )

        # Validate range
        if self.date_to < self.date_from:
            raise ValueError("date_to must be >= date_from")

        # Business rule: date_from must be >= 2005-04-20 (YouTube launch)
        youtube_launch = datetime(2005, 4, 20, tzinfo=timezone.utc)
        if self.date_from < youtube_launch:
            raise ValueError("date_from must be >= 2005-04-20 (YouTube launch date)")

        # Business rule: date_to must be <= now
        now = datetime.now(timezone.utc)
        if self.date_to > now:
            raise ValueError("date_to must be <= current time")

    def contains(self, date: datetime) -> bool:
        """Check if a date is within the range."""
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return self.date_from <= date <= self.date_to

    def duration_days(self) -> int:
        """Get duration in days."""
        delta = self.date_to - self.date_from
        return delta.days

    def is_valid(self) -> bool:
        """Check if the date range is valid."""
        return self.date_to >= self.date_from

