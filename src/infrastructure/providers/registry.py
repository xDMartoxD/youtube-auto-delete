"""Factory that wires a PlaylistProvider for each ProviderType."""

from src.domain.providers import PlaylistProvider, ProviderType
from src.infrastructure.providers.mock_provider import MockPlaylistProvider
from src.infrastructure.providers.youtube_provider import (
    YoutubePlaylistGateway,
    YoutubePlaylistProvider,
)


def build_providers(
    youtube_service: YoutubePlaylistGateway,
    user_id: str,
    *,
    spotify: PlaylistProvider | None = None,
    spotify_connectable: bool = False,
) -> dict[ProviderType, PlaylistProvider]:
    """
    Real integrations: YouTube and YouTube Music (same Data API), and Spotify
    when the user has connected their account (`spotify`).
    Mock integrations: Apple Music, Amazon Music, and Spotify until connected.
    """
    return {
        ProviderType.YOUTUBE: YoutubePlaylistProvider(
            youtube_service, ProviderType.YOUTUBE
        ),
        ProviderType.YOUTUBE_MUSIC: YoutubePlaylistProvider(
            youtube_service, ProviderType.YOUTUBE_MUSIC
        ),
        ProviderType.SPOTIFY: spotify
        or MockPlaylistProvider(
            ProviderType.SPOTIFY, user_id, connectable=spotify_connectable
        ),
        ProviderType.APPLE_MUSIC: MockPlaylistProvider(
            ProviderType.APPLE_MUSIC, user_id
        ),
        ProviderType.AMAZON_MUSIC: MockPlaylistProvider(
            ProviderType.AMAZON_MUSIC, user_id
        ),
    }
