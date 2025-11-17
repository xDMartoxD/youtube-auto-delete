"""Domain event: Session refreshed."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class SessionRefreshed:
    """Event raised when a user session is refreshed."""

    user_id: str
    session_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

