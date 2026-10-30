"""
Unit tests for PlaylistManagementService using an in-memory fake provider.
"""

import pytest

from src.application.services.playlist_management_service import (
    PlaylistManagementService,
)
from src.core.exceptions import (
    InvalidPlaylistOperationError,
    PlaylistNotFoundError,
    ProviderNotSupportedError,
)
from src.domain.entities.playlist import Playlist, Track
from src.domain.exceptions import PlaylistNotFoundDomainException
from src.domain.providers import PlaylistProvider, ProviderType
from src.domain.services.playlist_composition_service import CompositionMode


def track(track_id: str, item_id: str, available: bool = True) -> Track:
    return Track(item_id=item_id, track_id=track_id, title=track_id, is_available=available)


class FakeProvider(PlaylistProvider):
    provider_type = ProviderType.SPOTIFY

    def __init__(self, playlists: dict[str, list[Track]]):
        self.tracks = playlists
        self.created: list[str] = []

    async def list_playlists(self) -> list[Playlist]:
        return [
            Playlist(id=pid, name=pid, track_count=len(t)) for pid, t in self.tracks.items()
        ]

    async def get_tracks(self, playlist_id: str) -> list[Track]:
        if playlist_id not in self.tracks:
            raise PlaylistNotFoundDomainException(playlist_id)
        return list(self.tracks[playlist_id])

    async def remove_tracks(self, playlist_id: str, item_ids: list[str]) -> int:
        before = len(self.tracks[playlist_id])
        self.tracks[playlist_id] = [
            t for t in self.tracks[playlist_id] if t.item_id not in item_ids
        ]
        return before - len(self.tracks[playlist_id])

    async def create_playlist(self, name: str, description: str) -> Playlist:
        pid = f"new-{len(self.created)}"
        self.created.append(pid)
        self.tracks[pid] = []
        return Playlist(id=pid, name=name, description=description)

    async def add_tracks(self, playlist_id: str, track_ids: list[str]) -> int:
        self.tracks[playlist_id] += [track(tid, f"{playlist_id}-{tid}") for tid in track_ids]
        return len(track_ids)


@pytest.fixture
def provider():
    return FakeProvider(
        {
            "rock": [track("a", "r1"), track("b", "r2"), track("a", "r3")],
            "pop": [track("b", "p1"), track("c", "p2"), track("x", "p3", available=False)],
            "mix": [track("c", "m1")],
        }
    )


@pytest.fixture
def service(provider):
    return PlaylistManagementService({ProviderType.SPOTIFY: provider})


def track_ids(provider: FakeProvider, playlist_id: str) -> list[str]:
    return [t.track_id for t in provider.tracks[playlist_id]]


class TestPlaylistManagementService:
    """Tests for PlaylistManagementService."""

    @pytest.mark.asyncio
    async def test_unknown_provider_raises(self, service):
        with pytest.raises(ProviderNotSupportedError):
            await service.list_playlists(ProviderType.APPLE_MUSIC)

    @pytest.mark.asyncio
    async def test_get_tracks_reports_duplicates(self, service):
        tracks, duplicates = await service.get_tracks(ProviderType.SPOTIFY, "rock")

        assert len(tracks) == 3
        assert duplicates == ["r3"]

    @pytest.mark.asyncio
    async def test_missing_playlist_maps_to_api_error(self, service):
        with pytest.raises(PlaylistNotFoundError):
            await service.get_tracks(ProviderType.SPOTIFY, "nope")

    @pytest.mark.asyncio
    async def test_remove_tracks_deduplicates_ids(self, service, provider):
        removed = await service.remove_tracks(ProviderType.SPOTIFY, "rock", ["r1", "r1", "r3"])

        assert removed == 2
        assert track_ids(provider, "rock") == ["b"]

    @pytest.mark.asyncio
    async def test_remove_tracks_requires_selection(self, service):
        with pytest.raises(InvalidPlaylistOperationError):
            await service.remove_tracks(ProviderType.SPOTIFY, "rock", [])

    @pytest.mark.asyncio
    async def test_merge_into_existing_skips_tracks_already_there(self, service, provider):
        playlist, added = await service.merge_playlists(
            ProviderType.SPOTIFY, ["rock", "pop"], target_playlist_id="mix"
        )

        assert added == 2
        assert track_ids(provider, "mix") == ["c", "a", "b"]
        assert playlist.track_count == 3

    @pytest.mark.asyncio
    async def test_merge_into_new_playlist_skips_unavailable_tracks(self, service, provider):
        playlist, added = await service.merge_playlists(
            ProviderType.SPOTIFY, ["rock", "pop"], new_playlist_name="All"
        )

        assert playlist.name == "All"
        assert track_ids(provider, playlist.id) == ["a", "b", "c"]
        assert added == 3

    @pytest.mark.asyncio
    async def test_merge_rejects_target_that_is_a_source(self, service):
        with pytest.raises(InvalidPlaylistOperationError):
            await service.merge_playlists(
                ProviderType.SPOTIFY, ["rock", "mix"], target_playlist_id="mix"
            )

    @pytest.mark.asyncio
    async def test_merge_requires_destination(self, service):
        with pytest.raises(InvalidPlaylistOperationError):
            await service.merge_playlists(ProviderType.SPOTIFY, ["rock"])

    @pytest.mark.asyncio
    async def test_merge_with_unknown_target_maps_to_not_found(self, service):
        with pytest.raises(PlaylistNotFoundError):
            await service.merge_playlists(
                ProviderType.SPOTIFY, ["rock"], target_playlist_id="nope"
            )

    @pytest.mark.asyncio
    async def test_create_from_intersection(self, service, provider):
        playlist, added = await service.create_from_playlists(
            ProviderType.SPOTIFY, "Common", ["rock", "pop"], CompositionMode.INTERSECTION
        )

        assert added == 1
        assert track_ids(provider, playlist.id) == ["b"]

    @pytest.mark.asyncio
    async def test_create_with_empty_result_does_not_create_playlist(self, service, provider):
        with pytest.raises(InvalidPlaylistOperationError):
            await service.create_from_playlists(
                ProviderType.SPOTIFY, "None", ["rock", "mix"], CompositionMode.INTERSECTION
            )

        assert provider.created == []

    @pytest.mark.asyncio
    async def test_create_with_invalid_mode_arguments(self, service):
        with pytest.raises(InvalidPlaylistOperationError):
            await service.create_from_playlists(
                ProviderType.SPOTIFY, "Diff", ["rock"], CompositionMode.DIFFERENCE
            )
