from datetime import datetime
from pydantic import BaseModel, Field, model_validator

from src.domain.entities.playlist import Playlist, Track
from src.domain.providers import PlaylistProvider, ProviderType
from src.domain.services.playlist_composition_service import CompositionMode


class ProviderInfo(BaseModel):
    id: ProviderType = Field(description="Provider identifier")
    name: str = Field(description="Display name")
    is_mock: bool = Field(description="True when the provider serves demo data")

    @classmethod
    def from_provider(cls, provider: PlaylistProvider) -> "ProviderInfo":
        return cls(
            id=provider.provider_type,
            name=provider.provider_type.display_name,
            is_mock=provider.is_mock,
        )


class ProviderListResponse(BaseModel):
    providers: list[ProviderInfo]


class PlaylistResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    image_url: str | None = None
    track_count: int = 0
    owner: str | None = None

    @classmethod
    def from_entity(cls, playlist: Playlist) -> "PlaylistResponse":
        return cls(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            image_url=playlist.image_url,
            track_count=playlist.track_count,
            owner=playlist.owner,
        )


class PlaylistListResponse(BaseModel):
    provider: ProviderType
    playlists: list[PlaylistResponse]


class TrackResponse(BaseModel):
    item_id: str = Field(description="Entry id inside the playlist (use it to remove)")
    track_id: str = Field(description="Song/video id in the provider catalog")
    title: str
    artist: str | None = None
    album: str | None = None
    duration_ms: int | None = None
    image_url: str | None = None
    added_at: datetime | None = Field(None, description="When it was added to the playlist")
    is_available: bool = Field(True, description="False for deleted/private tracks")

    @classmethod
    def from_entity(cls, track: Track) -> "TrackResponse":
        return cls(
            item_id=track.item_id,
            track_id=track.track_id,
            title=track.title,
            artist=track.artist,
            album=track.album,
            duration_ms=track.duration_ms,
            image_url=track.image_url,
            added_at=track.added_at,
            is_available=track.is_available,
        )


class TrackListResponse(BaseModel):
    playlist_id: str
    tracks: list[TrackResponse]
    duplicate_item_ids: list[str] = Field(
        description="Entries that repeat a track already earlier in the playlist"
    )


class RemoveTracksRequest(BaseModel):
    item_ids: list[str] = Field(min_length=1, max_length=1000)

    model_config = {"extra": "forbid"}


class RemoveTracksResponse(BaseModel):
    removed_count: int
    requested_count: int


class MergePlaylistsRequest(BaseModel):
    source_playlist_ids: list[str] = Field(min_length=1, max_length=20)
    target_playlist_id: str | None = Field(
        None, description="Existing playlist that receives the tracks"
    )
    new_playlist_name: str | None = Field(
        None, min_length=1, max_length=150, description="Create a new playlist instead"
    )
    remove_duplicates: bool = True

    @model_validator(mode="after")
    def validate_destination(self):
        if bool(self.target_playlist_id) == bool(self.new_playlist_name):
            raise ValueError(
                "Provide exactly one of target_playlist_id or new_playlist_name"
            )
        return self

    model_config = {"extra": "forbid"}


class CreatePlaylistFromSourcesRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = Field("", max_length=1000)
    source_playlist_ids: list[str] = Field(min_length=1, max_length=20)
    mode: CompositionMode = Field(
        CompositionMode.UNION,
        description="union: all tracks; intersection: tracks in every source; "
        "difference: tracks of the first source not in the others",
    )
    remove_duplicates: bool = True

    model_config = {"extra": "forbid"}


class PlaylistOperationResponse(BaseModel):
    playlist: PlaylistResponse
    added_count: int
