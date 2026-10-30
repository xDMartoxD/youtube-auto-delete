"""Factory that wires a PlaylistProvider for each ProviderType."""

from src.domain.providers import PlaylistProvider, ProviderType
from src.infrastructure.providers.mock_provider import MockPlaylistProvider
from src.infrastructure.providers.youtube_provider import (
    YoutubePlaylistGateway,
    YoutubePlaylistProvider,
)


def build_providers(
    youtube_service: YoutubePlaylistGateway, user_id: str
) -> dict[ProviderType, PlaylistProvider]:
    """
    Real integrations: YouTube and YouTube Music (same Data API).
    Mock integrations: Spotify, Apple Music, Amazon Music. Replace the mock with a
    real adapter here once OAuth for that service is set up.
    """
    return {
        ProviderType.YOUTUBE: YoutubePlaylistProvider(
            youtube_service, ProviderType.YOUTUBE
        ),
        ProviderType.YOUTUBE_MUSIC: YoutubePlaylistProvider(
            youtube_service, ProviderType.YOUTUBE_MUSIC
        ),
        ProviderType.SPOTIFY: MockPlaylistProvider(ProviderType.SPOTIFY, user_id),
        ProviderType.APPLE_MUSIC: MockPlaylistProvider(
            ProviderType.APPLE_MUSIC, user_id
        ),
        ProviderType.AMAZON_MUSIC: MockPlaylistProvider(
            ProviderType.AMAZON_MUSIC, user_id
        ),
    }
