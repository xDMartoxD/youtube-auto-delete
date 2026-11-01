"""Spotify provider backed by the Spotify Web API."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.core.exceptions import ProviderRequestError
from src.domain.entities.playlist import Playlist, Track
from src.domain.entities.provider_connection import ProviderConnection
from src.domain.exceptions import PlaylistNotFoundDomainException
from src.domain.providers import PlaylistProvider, ProviderType
from src.domain.repositories.provider_connection_repository import (
    IProviderConnectionRepository,
)
from src.infrastructure.external_services.spotify_client import (
    SpotifyApiError,
    SpotifyClient,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 50
TRACK_PAGE_SIZE = 100
TRACK_FIELDS = (
    "next,items(added_at,is_local,track(uri,name,duration_ms,is_playable,type,"
    "artists(name),album(name,images)))"
)
ADDABLE_PREFIX = "spotify:track:"
ITEM_ID_SEPARATOR = "|"


@dataclass(frozen=True, slots=True)
class RemovalPlan:
    """How to remove specific occurrences when the API removes every copy of a URI."""

    uris_to_delete: list[str]
    reinserts: list[tuple[int, str]]  # (position, uri), applied in this order


def plan_removal(uris: list[str | None], selected: set[int]) -> RemovalPlan:
    """
    Spotify deletes all occurrences of a URI. To remove only the selected
    positions: delete every affected URI, then re-insert the kept copies at
    their final positions in ascending order (each insert lands exactly where
    the final playlist expects it, because everything before it is in place).
    """
    affected = {uris[i] for i in selected if uris[i]}
    final = [uri for i, uri in enumerate(uris) if i not in selected]
    reinserts = [(pos, uri) for pos, uri in enumerate(final) if uri in affected]
    return RemovalPlan(uris_to_delete=sorted(affected), reinserts=reinserts)


def make_item_id(position: int, uri: str) -> str:
    return f"{position}{ITEM_ID_SEPARATOR}{uri}"


def parse_item_id(item_id: str) -> tuple[int, str] | None:
    position, _, uri = item_id.partition(ITEM_ID_SEPARATOR)
    return (int(position), uri) if position.isdigit() and uri else None


def _image(images: list[dict[str, Any]] | None) -> str | None:
    # Spotify lists images largest first; pick the smallest that is still >= 64px
    if not images:
        return None
    suitable = [i for i in images if (i.get("width") or 300) >= 64]
    return (suitable[-1] if suitable else images[0]).get("url")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class SpotifyPlaylistProvider(PlaylistProvider):
    provider_type = ProviderType.SPOTIFY
    connectable = True

    def __init__(
        self,
        client: SpotifyClient,
        connection: ProviderConnection,
        connections: IProviderConnectionRepository,
    ):
        self._client = client
        self._connection = connection
        self._connections = connections
        self._user_id: str | None = None

    async def list_playlists(self) -> list[Playlist]:
        playlists = []
        async for item in self._paginate("/me/playlists", {"limit": PAGE_SIZE}):
            # Newer API responses name the track summary "items" instead of "tracks"
            summary = item.get("tracks") or item.get("items") or {}
            playlists.append(
                Playlist(
                    id=item["id"],
                    name=item.get("name") or "",
                    description=item.get("description") or "",
                    image_url=_image(item.get("images")),
                    track_count=summary.get("total", 0),
                    owner=(item.get("owner") or {}).get("display_name"),
                )
            )
        return playlists

    async def get_tracks(self, playlist_id: str) -> list[Track]:
        tracks = []
        for position, item in enumerate(await self._playlist_items(playlist_id)):
            track = item.get("track")
            if not track or track.get("type") != "track" or not track.get("uri"):
                continue  # podcast episodes and removed entries
            tracks.append(
                Track(
                    item_id=make_item_id(position, track["uri"]),
                    track_id=track["uri"],
                    title=track.get("name") or "Unknown track",
                    artist=", ".join(a["name"] for a in track.get("artists") or []),
                    album=(track.get("album") or {}).get("name"),
                    duration_ms=track.get("duration_ms"),
                    image_url=_image((track.get("album") or {}).get("images")),
                    added_at=_parse_datetime(item.get("added_at")),
                    is_available=bool(track.get("is_playable", True))
                    and not item.get("is_local"),
                )
            )
        return tracks

    async def remove_tracks(self, playlist_id: str, item_ids: list[str]) -> int:
        # Re-read the playlist so positions are current, and drop stale selections
        uris = [
            (item.get("track") or {}).get("uri")
            for item in await self._playlist_items(playlist_id)
        ]
        selected = set()
        for item_id in item_ids:
            parsed = parse_item_id(item_id)
            if parsed is None:
                continue
            position, uri = parsed
            if position < len(uris) and uris[position] == uri and uri.startswith(
                ADDABLE_PREFIX
            ):
                selected.add(position)
        if not selected:
            return 0

        plan = plan_removal(uris, selected)
        path = f"/playlists/{playlist_id}/tracks"
        for start in range(0, len(plan.uris_to_delete), TRACK_PAGE_SIZE):
            chunk = plan.uris_to_delete[start : start + TRACK_PAGE_SIZE]
            await self._call(
                "DELETE", path, json={"tracks": [{"uri": u} for u in chunk]}
            )
        for position, uri in plan.reinserts:
            await self._call("POST", path, json={"uris": [uri], "position": position})
        return len(selected)

    async def create_playlist(self, name: str, description: str) -> Playlist:
        user_id = await self._current_user_id()
        created = await self._call(
            "POST",
            f"/users/{user_id}/playlists",
            json={"name": name, "description": description, "public": False},
        )
        return Playlist(
            id=created["id"],
            name=created.get("name") or name,
            description=created.get("description") or "",
            owner=(created.get("owner") or {}).get("display_name"),
        )

    async def add_tracks(self, playlist_id: str, track_ids: list[str]) -> int:
        uris = [t for t in track_ids if t.startswith(ADDABLE_PREFIX)]
        for start in range(0, len(uris), TRACK_PAGE_SIZE):
            await self._call(
                "POST",
                f"/playlists/{playlist_id}/tracks",
                json={"uris": uris[start : start + TRACK_PAGE_SIZE]},
            )
        return len(uris)

    async def _playlist_items(self, playlist_id: str) -> list[dict[str, Any]]:
        params = {
            "limit": TRACK_PAGE_SIZE,
            "market": "from_token",
            "fields": TRACK_FIELDS,
        }
        return [
            item
            async for item in self._paginate(f"/playlists/{playlist_id}/tracks", params)
        ]

    async def _paginate(self, path: str, params: dict[str, Any]):
        page = await self._call("GET", path, params=params)
        while True:
            for item in page.get("items") or []:
                if item:
                    yield item
            if not page.get("next"):
                return
            page = await self._call("GET", page["next"])

    async def _current_user_id(self) -> str:
        if self._user_id is None:
            self._user_id = (await self._call("GET", "/me"))["id"]
        return self._user_id

    async def _access_token(self, force_refresh: bool = False) -> str:
        if force_refresh or self._connection.needs_refresh():
            try:
                grant = await self._client.refresh(self._connection.refresh_token)
            except SpotifyApiError as e:
                raise ProviderRequestError(
                    message=f"Spotify token refresh failed: {e}",
                    user_message="Your Spotify connection expired. Reconnect Spotify.",
                )
            self._connection = self._connection.with_tokens(
                grant.access_token, grant.expires_at, grant.refresh_token
            )
            await self._connections.save(self._connection)
        return self._connection.access_token

    async def _call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            try:
                return await self._client.request(
                    method, path, await self._access_token(), **kwargs
                )
            except SpotifyApiError as e:
                if e.status != 401:
                    raise
                # Token revoked or expired early: refresh once and retry
                return await self._client.request(
                    method, path, await self._access_token(force_refresh=True), **kwargs
                )
        except SpotifyApiError as e:
            raise self._to_app_error(e, path)

    @staticmethod
    def _to_app_error(error: SpotifyApiError, path: str) -> Exception:
        if error.status == 404 and path.startswith("/playlists/"):
            return PlaylistNotFoundDomainException(path.split("/")[2])
        if error.status == 403 and "regist" in error.message.lower():
            user_message = (
                "Your Spotify account isn't enabled for this app yet. Spotify apps "
                "in development mode only allow users added in the Spotify dashboard."
            )
        elif error.status == 403:
            user_message = "Spotify didn't allow this change. You can only edit playlists you own."
        elif error.status == 401:
            user_message = "Your Spotify connection expired. Reconnect Spotify."
        else:
            user_message = "Spotify returned an error, please try again"
        return ProviderRequestError(message=str(error), user_message=user_message)
