"""Provider-agnostic playlist and track entities."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class Track:
    """
    One entry of a playlist.

    `item_id` identifies the entry inside the playlist (used to remove it);
    `track_id` identifies the song/video in the provider's catalog (used to
    detect duplicates and to add it to other playlists).
    """

    item_id: str
    track_id: str
    title: str
    artist: str | None = None
    album: str | None = None
    duration_ms: int | None = None
    image_url: str | None = None
    added_at: datetime | None = None
    is_available: bool = True


@dataclass(slots=True, frozen=True)
class Playlist:
    """A user playlist on any provider."""

    id: str
    name: str
    description: str = ""
    image_url: str | None = None
    track_count: int = 0
    owner: str | None = None
