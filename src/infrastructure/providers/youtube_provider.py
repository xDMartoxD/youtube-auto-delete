"""YouTube / YouTube Music provider backed by the YouTube Data API."""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, Protocol

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from src.core.exceptions import AuthenticationFailedError, ProviderRequestError
from src.domain.entities.playlist import Playlist, Track
from src.domain.providers import PlaylistProvider, ProviderType
from src.schemas.youtube import PlaylistItemVideo


class YoutubePlaylistGateway(Protocol):
    """The YouTube operations this adapter needs (implemented by YoutubeService)."""

    async def get_all_user_playlists(self) -> list[dict[str, Any]]: ...

    async def get_all_playlist_items(
        self, playlist_id: str
    ) -> list[PlaylistItemVideo]: ...

    async def delete_playlist_videos(
        self,
        playlist_id: str,
        include_private_videos: bool,
        include_delete_videos: bool,
        item_ids: list[str] | None = None,
    ) -> int: ...

    async def create_playlist(
        self, title: str, description: str = "", privacy_status: str = "private"
    ) -> dict[str, Any]: ...

    async def add_videos_to_playlist(
        self, playlist_id: str, video_ids: list[str]
    ) -> int: ...

    def is_unavailable_video(self, item: PlaylistItemVideo) -> bool: ...


def _thumbnail_url(thumbnails: Any) -> str | None:
    """Pick a medium-sized thumbnail from a dict or Thumbnails model."""
    if not thumbnails:
        return None
    if not isinstance(thumbnails, dict):
        thumbnails = thumbnails.model_dump()
    for size in ("medium", "high", "default"):
        thumb = thumbnails.get(size)
        if thumb and thumb.get("url"):
            return thumb["url"]
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@contextmanager
def _youtube_errors_as_api_errors() -> Iterator[None]:
    """Map Google client failures to application exceptions."""
    try:
        yield
    except RefreshError as e:
        # Google rejected the access token (expired or revoked)
        raise AuthenticationFailedError(
            message=f"YouTube credentials rejected: {e}",
            user_message="Your Google session expired, please sign in again",
        )
    except HttpError as e:
        raise ProviderRequestError(
            message=f"YouTube API error: {e}",
            user_message="YouTube returned an error, please try again",
        )


class YoutubePlaylistProvider(PlaylistProvider):
    """
    Adapter from the PlaylistProvider port to the YouTube Data API.

    YouTube Music playlists are regular YouTube playlists, so the same adapter
    serves both provider types.
    """

    def __init__(
        self, youtube_service: YoutubePlaylistGateway, provider_type: ProviderType
    ):
        self._youtube = youtube_service
        self.provider_type = provider_type

    async def list_playlists(self) -> list[Playlist]:
        with _youtube_errors_as_api_errors():
            resources = await self._youtube.get_all_user_playlists()
        return [self._to_playlist(resource) for resource in resources]

    async def get_tracks(self, playlist_id: str) -> list[Track]:
        with _youtube_errors_as_api_errors():
            items = await self._youtube.get_all_playlist_items(playlist_id)
        return [self._to_track(item) for item in items]

    async def remove_tracks(self, playlist_id: str, item_ids: list[str]) -> int:
        with _youtube_errors_as_api_errors():
            return await self._youtube.delete_playlist_videos(
                playlist_id,
                include_private_videos=False,
                include_delete_videos=False,
                item_ids=item_ids,
            )

    async def create_playlist(self, name: str, description: str) -> Playlist:
        with _youtube_errors_as_api_errors():
            resource = await self._youtube.create_playlist(name, description)
        return self._to_playlist(resource)

    async def add_tracks(self, playlist_id: str, track_ids: list[str]) -> int:
        with _youtube_errors_as_api_errors():
            return await self._youtube.add_videos_to_playlist(playlist_id, track_ids)

    def _to_playlist(self, resource: dict[str, Any]) -> Playlist:
        snippet = resource.get("snippet") or {}
        content = resource.get("contentDetails") or {}
        return Playlist(
            id=resource["id"],
            name=snippet.get("title", ""),
            description=snippet.get("description") or "",
            image_url=_thumbnail_url(snippet.get("thumbnails")),
            track_count=content.get("itemCount", 0),
            owner=snippet.get("channelTitle"),
        )

    def _to_track(self, item: PlaylistItemVideo) -> Track:
        snippet = item.snippet
        return Track(
            item_id=item.id,
            track_id=snippet.resourceId.videoId,
            title=snippet.title,
            artist=snippet.videoOwnerChannelTitle,
            image_url=_thumbnail_url(snippet.thumbnails),
            added_at=_parse_datetime(snippet.publishedAt),
            is_available=not self._youtube.is_unavailable_video(item),
        )
