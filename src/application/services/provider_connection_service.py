"""Application service for linking a user's account on a music provider (OAuth)."""

import logging

from src.core.config import config
from src.core.exceptions import (
    InvalidPlaylistOperationError,
    ProviderNotSupportedError,
    ProviderRequestError,
)
from src.domain.entities.provider_connection import ProviderConnection
from src.domain.providers import ProviderType
from src.domain.repositories.provider_connection_repository import (
    IProviderConnectionRepository,
)
from src.infrastructure.external_services.spotify_client import (
    SpotifyApiError,
    SpotifyClient,
)
from src.infrastructure.services.oauth_state_service import OAuthStateService

logger = logging.getLogger(__name__)

# Providers whose accounts can be linked, and whether the app is configured for them
CONNECTABLE_PROVIDERS = {ProviderType.SPOTIFY: lambda: config.spotify_enabled}


def is_connectable(provider: ProviderType) -> bool:
    check = CONNECTABLE_PROVIDERS.get(provider)
    return bool(check and check())


class ProviderConnectionService:
    """Starts and completes the OAuth flow and stores the resulting tokens."""

    def __init__(
        self,
        spotify_client: SpotifyClient,
        connections: IProviderConnectionRepository,
        state_service: OAuthStateService | None = None,
    ):
        self._spotify = spotify_client
        self._connections = connections
        self._state = state_service or OAuthStateService()

    def authorize_url(self, user_id: str, provider: ProviderType) -> str:
        self._require_connectable(provider)
        return self._spotify.authorize_url(self._state.issue(user_id, provider))

    async def complete(self, provider: ProviderType, code: str, state: str) -> None:
        """Handle the provider's redirect back: verify `state`, then store tokens."""
        self._require_connectable(provider)
        try:
            user_id = self._state.verify(state, provider)
        except ValueError as e:
            raise InvalidPlaylistOperationError(
                message=str(e), user_message="The connection link expired, try again"
            )
        try:
            grant = await self._spotify.exchange_code(code)
        except SpotifyApiError as e:
            raise ProviderRequestError(
                message=f"Spotify code exchange failed: {e}",
                user_message="Spotify didn't accept the connection, try again",
            )
        await self._connections.save(
            ProviderConnection(
                user_id=user_id,
                provider=provider,
                access_token=grant.access_token,
                refresh_token=grant.refresh_token or "",
                expires_at=grant.expires_at,
                scope=grant.scope,
            )
        )
        logger.info(f"User {user_id} connected {provider}")

    async def find(
        self, user_id: str, provider: ProviderType
    ) -> ProviderConnection | None:
        if not is_connectable(provider):
            return None
        return await self._connections.find(user_id, provider)

    async def disconnect(self, user_id: str, provider: ProviderType) -> None:
        self._require_connectable(provider)
        await self._connections.delete(user_id, provider)
        logger.info(f"User {user_id} disconnected {provider}")

    @staticmethod
    def _require_connectable(provider: ProviderType) -> None:
        if not is_connectable(provider):
            raise ProviderNotSupportedError(
                message=f"Connecting {provider} accounts is not available"
            )
