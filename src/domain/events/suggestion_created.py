"""Domain event: Suggestion created."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class SuggestionCreated:
    """Event raised when a suggestion is created."""

    suggestion_id: str
    title: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

