"""Supported playlist providers."""

from enum import StrEnum


class ProviderType(StrEnum):
    """Identifier of each music/video service the app can manage playlists for."""

    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    AMAZON_MUSIC = "amazon_music"

    @property
    def display_name(self) -> str:
        return {
            ProviderType.YOUTUBE: "YouTube",
            ProviderType.YOUTUBE_MUSIC: "YouTube Music",
            ProviderType.SPOTIFY: "Spotify",
            ProviderType.APPLE_MUSIC: "Apple Music",
            ProviderType.AMAZON_MUSIC: "Amazon Music",
        }[self]
