"""Domain event: User authenticated."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class UserAuthenticated:
    """Event raised when a user successfully authenticates."""

    user_id: str
    email: str
    session_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

