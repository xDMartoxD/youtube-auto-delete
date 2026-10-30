"""
Unit tests for MockPlaylistProvider.
"""

import pytest

from src.domain.exceptions import PlaylistNotFoundDomainException
from src.domain.providers import ProviderType
from src.infrastructure.providers.mock_provider import (
    MockPlaylistProvider,
    reset_mock_libraries,
)


@pytest.fixture(autouse=True)
def clean_libraries():
    reset_mock_libraries()
    yield
    reset_mock_libraries()


@pytest.fixture
def provider():
    return MockPlaylistProvider(ProviderType.SPOTIFY, "user-1")


class TestMockPlaylistProvider:
    """Tests for MockPlaylistProvider."""

    @pytest.mark.asyncio
    async def test_seeded_library_is_deterministic_per_user(self):
        first = await MockPlaylistProvider(ProviderType.SPOTIFY, "user-1").list_playlists()
        reset_mock_libraries()
        second = await MockPlaylistProvider(ProviderType.SPOTIFY, "user-1").list_playlists()

        assert [p.id for p in first] == [p.id for p in second]
        assert all(p.track_count > 0 for p in first)

    @pytest.mark.asyncio
    async def test_users_get_separate_libraries(self, provider):
        playlist = (await provider.list_playlists())[0]
        tracks = await provider.get_tracks(playlist.id)

        await provider.remove_tracks(playlist.id, [tracks[0].item_id])
        other_user = MockPlaylistProvider(ProviderType.SPOTIFY, "user-2")

        assert playlist.id not in {p.id for p in await other_user.list_playlists()}

    @pytest.mark.asyncio
    async def test_remove_tracks_persists_between_instances(self, provider):
        playlist = (await provider.list_playlists())[0]
        tracks = await provider.get_tracks(playlist.id)

        removed = await provider.remove_tracks(
            playlist.id, [tracks[0].item_id, tracks[1].item_id, "unknown"]
        )
        again = MockPlaylistProvider(ProviderType.SPOTIFY, "user-1")

        assert removed == 2
        assert len(await again.get_tracks(playlist.id)) == len(tracks) - 2

    @pytest.mark.asyncio
    async def test_create_and_add_tracks(self, provider):
        source = (await provider.list_playlists())[0]
        available = [t for t in await provider.get_tracks(source.id) if t.is_available]

        created = await provider.create_playlist("New", "desc")
        added = await provider.add_tracks(
            created.id, [t.track_id for t in available[:3]] + ["missing"]
        )

        tracks = await provider.get_tracks(created.id)
        assert added == 3
        assert [t.track_id for t in tracks] == [t.track_id for t in available[:3]]
        assert len({t.item_id for t in tracks}) == 3

    @pytest.mark.asyncio
    async def test_unknown_playlist_raises_domain_exception(self, provider):
        with pytest.raises(PlaylistNotFoundDomainException):
            await provider.get_tracks("nope")
