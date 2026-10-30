"""In-memory provider that serves demo data for services without a real integration."""

import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.domain.entities.playlist import Playlist, Track
from src.domain.exceptions import PlaylistNotFoundDomainException
from src.domain.providers import PlaylistProvider, ProviderType
from src.infrastructure.providers.mock_catalog import (
    CATALOG,
    PLAYLIST_NAMES,
    UNAVAILABLE_TITLE,
)


class MockLibrary:
    """One user's playlists on one mock provider."""

    def __init__(self) -> None:
        self.playlists: dict[str, Playlist] = {}
        self.tracks: dict[str, list[Track]] = {}


# Libraries live for the lifetime of the process, keyed by (provider, user).
# Good enough for a demo: changes survive across requests but not restarts.
_libraries: dict[tuple[ProviderType, str], MockLibrary] = {}


def reset_mock_libraries() -> None:
    """Forget all mock data (used by tests)."""
    _libraries.clear()


class MockPlaylistProvider(PlaylistProvider):
    """Demo provider with realistic, deterministic data per user."""

    is_mock = True

    def __init__(self, provider_type: ProviderType, user_id: str):
        self.provider_type = provider_type
        self._user_id = user_id
        key = (provider_type, user_id)
        if key not in _libraries:
            _libraries[key] = self._seed_library()
        self._library = _libraries[key]

    async def list_playlists(self) -> list[Playlist]:
        return [
            replace(playlist, track_count=len(self._library.tracks[playlist.id]))
            for playlist in self._library.playlists.values()
        ]

    async def get_tracks(self, playlist_id: str) -> list[Track]:
        return list(self._tracks_of(playlist_id))

    async def remove_tracks(self, playlist_id: str, item_ids: list[str]) -> int:
        tracks = self._tracks_of(playlist_id)
        to_remove = set(item_ids)
        kept = [t for t in tracks if t.item_id not in to_remove]
        self._library.tracks[playlist_id] = kept
        return len(tracks) - len(kept)

    async def create_playlist(self, name: str, description: str) -> Playlist:
        playlist = Playlist(
            id=self._new_id("playlist"),
            name=name,
            description=description,
            owner="You",
        )
        self._library.playlists[playlist.id] = playlist
        self._library.tracks[playlist.id] = []
        return playlist

    async def add_tracks(self, playlist_id: str, track_ids: list[str]) -> int:
        tracks = self._tracks_of(playlist_id)
        catalog = self._catalog_by_id()
        now = datetime.now(timezone.utc)
        added = 0
        for track_id in track_ids:
            source = catalog.get(track_id)
            if source is None or not source.is_available:
                continue
            tracks.append(
                replace(source, item_id=self._new_id("item"), added_at=now)
            )
            added += 1
        return added

    def _tracks_of(self, playlist_id: str) -> list[Track]:
        if playlist_id not in self._library.tracks:
            raise PlaylistNotFoundDomainException(playlist_id)
        return self._library.tracks[playlist_id]

    def _catalog_by_id(self) -> dict[str, Track]:
        """Every track known in this library, keyed by track id."""
        return {
            t.track_id: t for tracks in self._library.tracks.values() for t in tracks
        }

    def _new_id(self, kind: str) -> str:
        return f"{self.provider_type}:{kind}:{uuid4().hex[:12]}"

    def _seed_library(self) -> MockLibrary:
        """Build the same starting library every time for a given user."""
        rng = random.Random(f"{self.provider_type}:{self._user_id}")
        library = MockLibrary()
        now = datetime.now(timezone.utc)

        catalog = [
            Track(
                item_id="",
                track_id=f"{self.provider_type}:track:{index}",
                title=title,
                artist=artist,
                album=album,
                duration_ms=duration_ms,
            )
            for index, (title, artist, album, duration_ms) in enumerate(CATALOG)
        ]

        for name, description in PLAYLIST_NAMES[self.provider_type]:
            playlist_id = f"{self.provider_type}:playlist:{rng.getrandbits(48):012x}"
            picked = rng.sample(catalog, rng.randint(12, 22))
            # Simulate real-world mess: a few repeats and songs pulled from the catalog
            picked += rng.sample(picked, rng.randint(1, 3))
            rng.shuffle(picked)

            tracks = []
            for position, track in enumerate(picked):
                added_at = now - timedelta(days=rng.randint(1, 1500))
                tracks.append(
                    replace(
                        track,
                        item_id=f"{playlist_id}:item:{position}",
                        added_at=added_at,
                    )
                )
            for position in rng.sample(range(len(tracks)), rng.randint(0, 2)):
                tracks[position] = replace(
                    tracks[position],
                    title=UNAVAILABLE_TITLE,
                    artist=None,
                    album=None,
                    track_id=f"{self.provider_type}:removed:{rng.getrandbits(32):08x}",
                    is_available=False,
                )
            tracks.sort(key=lambda t: t.added_at or now)

            library.playlists[playlist_id] = Playlist(
                id=playlist_id, name=name, description=description, owner="You"
            )
            library.tracks[playlist_id] = tracks

        return library
