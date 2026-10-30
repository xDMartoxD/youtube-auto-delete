"""Application service for provider-agnostic playlist management."""

import asyncio
import logging
from contextlib import contextmanager
from dataclasses import replace
from typing import Iterator

from src.core.exceptions import (
    InvalidPlaylistOperationError,
    PlaylistNotFoundError,
    ProviderNotSupportedError,
)
from src.domain.entities.playlist import Playlist, Track
from src.domain.exceptions import PlaylistNotFoundDomainException
from src.domain.providers import PlaylistProvider, ProviderType
from src.domain.services.playlist_composition_service import (
    CompositionMode,
    PlaylistCompositionService,
)

logger = logging.getLogger(__name__)


@contextmanager
def _domain_errors_as_api_errors() -> Iterator[None]:
    """Map domain exceptions raised by providers to application exceptions."""
    try:
        yield
    except PlaylistNotFoundDomainException as e:
        raise PlaylistNotFoundError(message=e.message, user_message="Playlist not found")


class PlaylistManagementService:
    """
    Application service - orchestrates providers and the composition domain service.
    Clean up, merge and build playlists on any supported provider.
    """

    def __init__(
        self,
        providers: dict[ProviderType, PlaylistProvider],
        composition_service: PlaylistCompositionService | None = None,
    ):
        self._providers = providers
        self._composition = composition_service or PlaylistCompositionService()

    def list_providers(self) -> list[PlaylistProvider]:
        return list(self._providers.values())

    def _provider(self, provider_type: ProviderType) -> PlaylistProvider:
        provider = self._providers.get(provider_type)
        if provider is None:
            raise ProviderNotSupportedError(
                message=f"Provider '{provider_type}' is not available"
            )
        return provider

    async def list_playlists(self, provider_type: ProviderType) -> list[Playlist]:
        with _domain_errors_as_api_errors():
            return await self._provider(provider_type).list_playlists()

    async def get_tracks(
        self, provider_type: ProviderType, playlist_id: str
    ) -> tuple[list[Track], list[str]]:
        """Tracks of a playlist plus the item ids that repeat an earlier track."""
        with _domain_errors_as_api_errors():
            tracks = await self._provider(provider_type).get_tracks(playlist_id)
        duplicates = self._composition.find_duplicates(tracks)
        return tracks, [t.item_id for t in duplicates]

    async def remove_tracks(
        self, provider_type: ProviderType, playlist_id: str, item_ids: list[str]
    ) -> int:
        if not item_ids:
            raise InvalidPlaylistOperationError(
                message="No tracks selected", user_message="Select at least one track"
            )
        unique_ids = list(dict.fromkeys(item_ids))
        with _domain_errors_as_api_errors():
            removed = await self._provider(provider_type).remove_tracks(
                playlist_id, unique_ids
            )
        logger.info(
            f"Removed {removed}/{len(unique_ids)} tracks from {provider_type}:{playlist_id}"
        )
        return removed

    async def merge_playlists(
        self,
        provider_type: ProviderType,
        source_playlist_ids: list[str],
        target_playlist_id: str | None = None,
        new_playlist_name: str | None = None,
        remove_duplicates: bool = True,
    ) -> tuple[Playlist, int]:
        """
        Copy the tracks of the sources into an existing playlist or a new one.

        Returns:
            The target playlist and how many tracks were added to it
        """
        sources = self._validate_sources(source_playlist_ids)
        if target_playlist_id and target_playlist_id in sources:
            raise InvalidPlaylistOperationError(
                message="Target playlist is also a source",
                user_message="The destination playlist can't also be a source",
            )
        if not target_playlist_id and not new_playlist_name:
            raise InvalidPlaylistOperationError(
                message="Missing merge destination",
                user_message="Choose a destination playlist or a name for a new one",
            )

        provider = self._provider(provider_type)
        with _domain_errors_as_api_errors():
            source_tracks = await self._fetch_sources(provider, sources)
            incoming = self._composition.compose(
                source_tracks, CompositionMode.UNION, remove_duplicates
            )

            if target_playlist_id:
                target = await self._find_playlist(provider, target_playlist_id)
                if remove_duplicates:
                    existing = await provider.get_tracks(target_playlist_id)
                    incoming = self._composition.tracks_missing_from(
                        existing, incoming
                    )
            else:
                target = await provider.create_playlist(
                    new_playlist_name or "", "Merged with PlaylistMaster"
                )

            return await self._fill(provider, target, incoming)

    async def create_from_playlists(
        self,
        provider_type: ProviderType,
        name: str,
        source_playlist_ids: list[str],
        mode: CompositionMode = CompositionMode.UNION,
        remove_duplicates: bool = True,
        description: str = "",
    ) -> tuple[Playlist, int]:
        """Create a new playlist from a set operation over the source playlists."""
        sources = self._validate_sources(source_playlist_ids)
        provider = self._provider(provider_type)
        with _domain_errors_as_api_errors():
            source_tracks = await self._fetch_sources(provider, sources)

        try:
            tracks = self._composition.compose(source_tracks, mode, remove_duplicates)
        except ValueError as e:
            raise InvalidPlaylistOperationError(message=str(e), user_message=str(e))
        if not tracks:
            raise InvalidPlaylistOperationError(
                message="Composition produced an empty playlist",
                user_message="Those playlists have no tracks in common for this mode",
            )

        with _domain_errors_as_api_errors():
            playlist = await provider.create_playlist(name, description)
            return await self._fill(provider, playlist, tracks)

    def _validate_sources(self, source_playlist_ids: list[str]) -> list[str]:
        sources = list(dict.fromkeys(source_playlist_ids))
        if not sources:
            raise InvalidPlaylistOperationError(
                message="No source playlists",
                user_message="Select at least one source playlist",
            )
        return sources

    async def _fetch_sources(
        self, provider: PlaylistProvider, playlist_ids: list[str]
    ) -> list[list[Track]]:
        return list(
            await asyncio.gather(*(provider.get_tracks(pid) for pid in playlist_ids))
        )

    async def _find_playlist(
        self, provider: PlaylistProvider, playlist_id: str
    ) -> Playlist:
        for playlist in await provider.list_playlists():
            if playlist.id == playlist_id:
                return playlist
        raise PlaylistNotFoundDomainException(playlist_id)

    async def _fill(
        self, provider: PlaylistProvider, playlist: Playlist, tracks: list[Track]
    ) -> tuple[Playlist, int]:
        """Add only playable tracks; unavailable ones can't be re-added anywhere."""
        track_ids = [t.track_id for t in tracks if t.is_available]
        added = await provider.add_tracks(playlist.id, track_ids) if track_ids else 0
        return replace(playlist, track_count=playlist.track_count + added), added
