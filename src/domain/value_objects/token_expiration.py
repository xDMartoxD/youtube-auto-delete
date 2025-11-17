"""Value object for token expiration."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class TokenExpiration:
    """Value object representing token expiration with business rules."""

    expires_at: int  # Unix timestamp
    refresh_expires_at: int  # Unix timestamp

    def __post_init__(self) -> None:
        """Validate expiration times."""
        if self.expires_at <= 0:
            raise ValueError("expires_at must be a positive timestamp")
        if self.refresh_expires_at <= 0:
            raise ValueError("refresh_expires_at must be a positive timestamp")
        if self.refresh_expires_at < self.expires_at:
            raise ValueError("refresh_expires_at must be >= expires_at")

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Check if the token is expired."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        current_timestamp = int(current_time.timestamp())
        return current_timestamp >= self.expires_at

    def is_refresh_expired(self, current_time: datetime | None = None) -> bool:
        """Check if the refresh token is expired."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        current_timestamp = int(current_time.timestamp())
        return current_timestamp >= self.refresh_expires_at

    def is_fully_expired(self, current_time: datetime | None = None) -> bool:
        """Check if both tokens are expired."""
        return self.is_expired(current_time) and self.is_refresh_expired(current_time)

    def time_until_expiry(self, current_time: datetime | None = None) -> int:
        """Returns seconds until expiration (negative if expired)."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        current_timestamp = int(current_time.timestamp())
        return self.expires_at - current_timestamp

