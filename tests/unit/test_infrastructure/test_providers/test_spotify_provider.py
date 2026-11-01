"""
Unit tests for the Spotify provider, against a fake Web API that mimics
Spotify's semantics (DELETE removes every occurrence of a URI).
"""

import itertools
import time

import pytest
from unittest.mock import AsyncMock

from src.core.exceptions import ProviderRequestError
from src.domain.entities.provider_connection import ProviderConnection
from src.domain.exceptions import PlaylistNotFoundDomainException
from src.domain.providers import ProviderType
from src.infrastructure.external_services.spotify_client import (
    SpotifyApiError,
    TokenGrant,
)
from src.infrastructure.providers.spotify_provider import (
    SpotifyPlaylistProvider,
    make_item_id,
    plan_removal,
)


def apply_spotify_semantics(uris, plan):
    """What Spotify does with a RemovalPlan."""
    result = [u for u in uris if u not in set(plan.uris_to_delete)]
    for position, uri in plan.reinserts:
        result.insert(position, uri)
    return result


class TestPlanRemoval:
    @pytest.mark.parametrize(
        "uris,selected",
        [
            (["a", "b", "a", "c", "a"], {2}),  # one duplicate in the middle
            (["a", "b", "a", "c", "a"], {0, 4}),  # first and last copy
            (["a", "a", "a"], {1, 2}),
            (["a", "b", "c"], {0, 1, 2}),  # everything
            (["a", None, "b", "a"], {3}),  # entries without a URI stay put
        ],
    )
    def test_final_playlist_keeps_everything_not_selected(self, uris, selected):
        plan = plan_removal(uris, selected)

        expected = [u for i, u in enumerate(uris) if i not in selected]
        assert apply_spotify_semantics(uris, plan) == expected

    def test_exhaustive_small_playlists(self):
        uris = ["a", "b", "a", "c", "b", "a"]
        for size in range(1, len(uris) + 1):
            for selected in itertools.combinations(range(len(uris)), size):
                plan = plan_removal(uris, set(selected))
                expected = [u for i, u in enumerate(uris) if i not in selected]
                assert apply_spotify_semantics(uris, plan) == expected

    def test_unique_tracks_need_no_reinserts(self):
        plan = plan_removal(["a", "b", "c"], {1})

        assert plan.uris_to_delete == ["b"]
        assert plan.reinserts == []


def track(uri, name=None, playable=True):
    return {
        "added_at": "2025-01-02T03:04:05Z",
        "is_local": False,
        "track": {
            "uri": uri,
            "name": name or uri,
            "type": "track",
            "duration_ms": 1000,
            "is_playable": playable,
            "artists": [{"name": "Artist"}],
            "album": {"name": "Album", "images": [{"url": "https://img", "width": 300}]},
        },
    }


class FakeSpotify:
    """In-memory Web API: playlists of URIs, pagination of 2 items per page."""

    def __init__(self):
        self.playlists = {"p1": ["spotify:track:a", "spotify:track:b", "spotify:track:a"]}
        self.tokens_used = []
        self.expired_tokens = set()
        self.refresh = AsyncMock(
            return_value=TokenGrant("fresh", int(time.time()) + 3600, None, "")
        )

    async def request(self, method, path, token, *, params=None, json=None):
        self.tokens_used.append(token)
        if token in self.expired_tokens:
            raise SpotifyApiError(401, "The access token expired")
        path = path.replace("https://api.spotify.com/v1", "")
        base, _, offset = path.partition("?offset=")
        offset = int(offset or 0)

        if base == "/me":
            return {"id": "me"}
        if base == "/me/playlists":
            return {"items": [{"id": "p1", "name": "Mix", "tracks": {"total": 3}}], "next": None}
        if base.startswith("/users/me/playlists"):
            self.playlists["new"] = []
            return {"id": "new", "name": json["name"]}

        playlist_id = base.split("/")[2]
        if playlist_id not in self.playlists:
            raise SpotifyApiError(404, "Not found")
        uris = self.playlists[playlist_id]
        if method == "GET":
            page = uris[offset : offset + 2]
            more = offset + 2 < len(uris)
            return {
                "items": [track(u) for u in page],
                "next": f"https://api.spotify.com/v1{base}?offset={offset + 2}" if more else None,
            }
        if method == "DELETE":
            gone = {t["uri"] for t in json["tracks"]}
            self.playlists[playlist_id] = [u for u in uris if u not in gone]
            return {"snapshot_id": "s"}
        if method == "POST":
            if "position" in json:
                for i, uri in enumerate(json["uris"]):
                    uris.insert(json["position"] + i, uri)
            else:
                uris.extend(json["uris"])
            return {"snapshot_id": "s"}
        raise AssertionError(f"unexpected {method} {path}")


@pytest.fixture
def fake():
    return FakeSpotify()


@pytest.fixture
def connections():
    return AsyncMock()


def make_provider(fake, connections, expires_in=3600, token="valid"):
    connection = ProviderConnection(
        user_id="u1",
        provider=ProviderType.SPOTIFY,
        access_token=token,
        refresh_token="refresh",
        expires_at=int(time.time()) + expires_in,
    )
    return SpotifyPlaylistProvider(fake, connection, connections)


class TestSpotifyPlaylistProvider:
    @pytest.mark.asyncio
    async def test_reads_all_pages_with_positions_in_item_ids(self, fake, connections):
        tracks = await make_provider(fake, connections).get_tracks("p1")

        assert [t.track_id for t in tracks] == [
            "spotify:track:a",
            "spotify:track:b",
            "spotify:track:a",
        ]
        assert tracks[2].item_id == make_item_id(2, "spotify:track:a")
        assert tracks[0].artist == "Artist" and tracks[0].album == "Album"

    @pytest.mark.asyncio
    async def test_removes_only_the_selected_duplicate(self, fake, connections):
        provider = make_provider(fake, connections)

        removed = await provider.remove_tracks(
            "p1", [make_item_id(2, "spotify:track:a")]
        )

        assert removed == 1
        assert fake.playlists["p1"] == ["spotify:track:a", "spotify:track:b"]

    @pytest.mark.asyncio
    async def test_ignores_stale_selections(self, fake, connections):
        provider = make_provider(fake, connections)

        removed = await provider.remove_tracks(
            "p1", [make_item_id(1, "spotify:track:a")]  # position 1 is now "b"
        )

        assert removed == 0
        assert len(fake.playlists["p1"]) == 3

    @pytest.mark.asyncio
    async def test_create_and_add_tracks(self, fake, connections):
        provider = make_provider(fake, connections)

        playlist = await provider.create_playlist("New", "")
        added = await provider.add_tracks(
            playlist.id, ["spotify:track:x", "spotify:local:skip", "spotify:track:y"]
        )

        assert added == 2
        assert fake.playlists["new"] == ["spotify:track:x", "spotify:track:y"]

    @pytest.mark.asyncio
    async def test_refreshes_expiring_token_and_persists_it(self, fake, connections):
        provider = make_provider(fake, connections, expires_in=10)

        await provider.list_playlists()

        fake.refresh.assert_awaited_once_with("refresh")
        assert fake.tokens_used == ["fresh"]
        saved = connections.save.await_args.args[0]
        assert saved.access_token == "fresh" and saved.refresh_token == "refresh"

    @pytest.mark.asyncio
    async def test_retries_once_after_401(self, fake, connections):
        fake.expired_tokens.add("revoked")
        provider = make_provider(fake, connections, token="revoked")

        playlists = await provider.list_playlists()

        assert [p.name for p in playlists] == ["Mix"]
        assert fake.tokens_used == ["revoked", "fresh"]

    @pytest.mark.asyncio
    async def test_failed_refresh_asks_to_reconnect(self, fake, connections):
        fake.refresh.side_effect = SpotifyApiError(400, "invalid_grant")
        provider = make_provider(fake, connections, expires_in=10)

        with pytest.raises(ProviderRequestError) as error:
            await provider.list_playlists()

        assert "Reconnect Spotify" in error.value.user_message

    @pytest.mark.asyncio
    async def test_unknown_playlist_raises_domain_not_found(self, fake, connections):
        with pytest.raises(PlaylistNotFoundDomainException):
            await make_provider(fake, connections).get_tracks("nope")

    @pytest.mark.asyncio
    async def test_development_mode_allowlist_error_is_explained(self, connections):
        fake = AsyncMock()
        fake.request.side_effect = SpotifyApiError(
            403, "Check settings on developer.spotify.com/dashboard, the user may not be registered."
        )
        provider = make_provider(fake, connections)

        with pytest.raises(ProviderRequestError) as error:
            await provider.list_playlists()

        assert "development mode" in error.value.user_message
