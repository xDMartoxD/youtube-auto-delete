"""A user's OAuth link to a music provider other than Google (e.g. Spotify)."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from src.domain.providers.provider_type import ProviderType

# Refresh a little before expiry so a request never starts with a dying token
REFRESH_LEEWAY_SECONDS = 60


@dataclass(slots=True, frozen=True)
class ProviderConnection:
    user_id: str
    provider: ProviderType
    access_token: str
    refresh_token: str
    expires_at: int  # unix timestamp
    scope: str = ""

    def needs_refresh(self, now: datetime | None = None) -> bool:
        current = int((now or datetime.now(timezone.utc)).timestamp())
        return current >= self.expires_at - REFRESH_LEEWAY_SECONDS

    def with_tokens(
        self, access_token: str, expires_at: int, refresh_token: str | None = None
    ) -> "ProviderConnection":
        """Copy with refreshed tokens; providers may or may not rotate the refresh token."""
        return replace(
            self,
            access_token=access_token,
            expires_at=expires_at,
            refresh_token=refresh_token or self.refresh_token,
        )
