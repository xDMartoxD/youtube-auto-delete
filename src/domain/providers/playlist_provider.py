"""Port that every playlist provider (YouTube, Spotify, ...) implements."""

from abc import ABC, abstractmethod

from src.domain.entities.playlist import Playlist, Track
from src.domain.providers.provider_type import ProviderType


class PlaylistProvider(ABC):
    """
    Domain port for a music/video service.

    Implementations live in the infrastructure layer. `is_mock` is True for
    providers that serve demo data instead of talking to the real service.
    """

    provider_type: ProviderType
    is_mock: bool = False

    @abstractmethod
    async def list_playlists(self) -> list[Playlist]:
        """Return every playlist owned by the current user."""

    @abstractmethod
    async def get_tracks(self, playlist_id: str) -> list[Track]:
        """Return all entries of a playlist, in playlist order."""

    @abstractmethod
    async def remove_tracks(self, playlist_id: str, item_ids: list[str]) -> int:
        """Remove playlist entries by item id. Returns how many were removed."""

    @abstractmethod
    async def create_playlist(self, name: str, description: str) -> Playlist:
        """Create an empty playlist."""

    @abstractmethod
    async def add_tracks(self, playlist_id: str, track_ids: list[str]) -> int:
        """Append catalog tracks to a playlist. Returns how many were added."""
