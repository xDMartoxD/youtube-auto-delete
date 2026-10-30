"""
Unit tests for YoutubePlaylistProvider error mapping and conversion.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from src.core.exceptions import AuthenticationFailedError, ProviderRequestError
from src.domain.providers import ProviderType
from src.infrastructure.providers.youtube_provider import YoutubePlaylistProvider


@pytest.fixture
def gateway():
    return AsyncMock()


@pytest.fixture
def provider(gateway):
    return YoutubePlaylistProvider(gateway, ProviderType.YOUTUBE)


class TestYoutubePlaylistProvider:
    """Tests for YoutubePlaylistProvider."""

    @pytest.mark.asyncio
    async def test_rejected_credentials_map_to_authentication_error(
        self, provider, gateway
    ):
        gateway.get_all_user_playlists.side_effect = RefreshError("expired")

        with pytest.raises(AuthenticationFailedError):
            await provider.list_playlists()

    @pytest.mark.asyncio
    async def test_api_errors_map_to_provider_error(self, provider, gateway):
        gateway.add_videos_to_playlist.side_effect = HttpError(
            MagicMock(status=500), b"boom"
        )

        with pytest.raises(ProviderRequestError):
            await provider.add_tracks("playlist", ["video"])

    @pytest.mark.asyncio
    async def test_converts_playlists(self, provider, gateway):
        gateway.get_all_user_playlists.return_value = [
            {
                "id": "PL1",
                "snippet": {
                    "title": "Mix",
                    "channelTitle": "Me",
                    "thumbnails": {"medium": {"url": "https://img"}},
                },
                "contentDetails": {"itemCount": 7},
            }
        ]

        [playlist] = await provider.list_playlists()

        assert (playlist.id, playlist.name, playlist.track_count) == ("PL1", "Mix", 7)
        assert playlist.image_url == "https://img"
