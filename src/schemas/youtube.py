from typing import Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone


class PaginationParams(BaseModel):
    """Pagination parameters for YouTube API."""

    max_results: int = Field(
        25, ge=1, le=50, description="Maximum number of results per page"
    )
    page_token: str | None = Field(None, description="Page token for pagination")

    model_config = {"extra": "forbid"}


class DateRangeParams(BaseModel):
    """Parameters to filter by date range."""

    date_from: datetime = Field(
        description="Start date (ISO 8601). Filters videos added to playlist from this date.",
        alias="date_from",
    )
    date_to: datetime = Field(
        description="End date (ISO 8601). Filters videos added to playlist until this date.",
        alias="date_to",
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        """Validates that date_to is greater than or equal to date_from."""
        if self.date_to < self.date_from:
            raise ValueError("date_to must be greater than or equal to date_from")
        if self.date_from < datetime(2005, 4, 20, tzinfo=timezone.utc):
            raise ValueError("date_from must be greater than or equal to 2005-04-20")
        if self.date_to > datetime.now(timezone.utc):
            raise ValueError("date_to must be less than or equal to the current date")
        return self

    model_config = {"extra": "forbid"}


class PlaylistVideoQueryParams(BaseModel):
    """Combined pagination and date filter parameters for playlist videos."""

    max_results: int = Field(
        default=25,
        ge=1,
        le=50,
        description="Maximum number of results per page",
    )
    page_token: str | None = Field(
        default=None, description="Page token for pagination"
    )
    date_from: datetime | None = Field(
        default=None,
        description="Start date (ISO 8601). Filters videos added to playlist from this date.",
        alias="date_from",
    )
    date_to: datetime | None = Field(
        default=None,
        description="End date (ISO 8601). Filters videos added to playlist until this date.",
        alias="date_to",
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        """Validates that if dates are provided, both are present and valid."""
        has_date_from = self.date_from is not None
        has_date_to = self.date_to is not None

        # If any date is provided, both must be present
        if has_date_from and not has_date_to:
            raise ValueError(
                "date_to is required when using date filter. Provide both dates: date_from and date_to."
            )
        if has_date_to and not has_date_from:
            raise ValueError(
                "date_from is required when using date filter. Provide both dates: date_from and date_to."
            )

        # If both dates are present, validate the range
        if has_date_from and has_date_to:
            # Type narrowing: sabemos que ambos son datetime, no None
            date_from = self.date_from
            date_to = self.date_to
            assert date_from is not None and date_to is not None  # Para type checker

            if date_to < date_from:
                raise ValueError("date_to must be greater than or equal to date_from")
            if date_from < datetime(2005, 4, 20, tzinfo=timezone.utc):
                raise ValueError(
                    "date_from must be greater than or equal to 2005-04-20"
                )
            if date_to > datetime.now(timezone.utc):
                raise ValueError(
                    "date_to must be less than or equal to the current date"
                )

        return self

    @property
    def pagination(self) -> PaginationParams:
        """Returns pagination parameters."""
        return PaginationParams(
            max_results=self.max_results, page_token=self.page_token
        )

    @property
    def date_range(self) -> DateRangeParams | None:
        """Returns date range parameters if present."""
        if self.date_from is None or self.date_to is None:
            return None
        return DateRangeParams(date_from=self.date_from, date_to=self.date_to)

    model_config = {"extra": "forbid"}


class PageInfo(BaseModel):
    totalResults: int
    resultsPerPage: int


class PlaylistSnippet(BaseModel):
    title: str
    description: str | None = None
    publishedAt: str | None = None
    channelId: str | None = None
    channelTitle: str | None = None
    thumbnails: dict[str, Any] | None = None


class PlaylistItem(BaseModel):
    kind: str
    etag: str
    id: str
    snippet: PlaylistSnippet | None = None


class YoutubePlaylistListResponse(BaseModel):
    kind: str = Field("youtube#playlistListResponse", description="Response type")
    etag: str = Field(description="Response etag")
    nextPageToken: str | None = Field(None, description="Next page token")
    pageInfo: PageInfo = Field(description="Page information")
    items: list[PlaylistItem] = Field(description="List of playlist items")


# Schemas for PlaylistItemVideo (video items in a playlist)
class Thumbnail(BaseModel):
    """Individual thumbnail with specific size."""

    url: str
    width: int
    height: int


class Thumbnails(BaseModel):
    """All available thumbnails for a video."""

    default: Thumbnail | None = None
    medium: Thumbnail | None = None
    high: Thumbnail | None = None
    standard: Thumbnail | None = None
    maxres: Thumbnail | None = None


class ResourceId(BaseModel):
    """Resource ID that identifies the video."""

    kind: str = Field(description="Resource type, usually 'youtube#video'")
    videoId: str = Field(description="YouTube video ID")


class PlaylistItemSnippet(BaseModel):
    """Complete snippet of a playlist item."""

    publishedAt: str = Field(description="Publication date of the item in the playlist")
    channelId: str = Field(
        description="Channel ID that added the video to the playlist"
    )
    title: str = Field(description="Video title")
    description: str = Field(default="", description="Video description")
    thumbnails: Thumbnails | None = None
    channelTitle: str = Field(description="Name of the channel that added the video")
    playlistId: str = Field(description="Playlist ID")
    position: int = Field(description="Video position in the playlist")
    resourceId: ResourceId = Field(description="Resource ID (video)")
    videoOwnerChannelTitle: str | None = Field(
        None, description="Title of the channel that uploaded the video"
    )
    videoOwnerChannelId: str | None = Field(
        None, description="ID of the channel that uploaded the video"
    )


class ContentDetails(BaseModel):
    """Video content details."""

    videoId: str = Field(description="Video ID")
    videoPublishedAt: str | None = Field(
        None, description="Original video publication date"
    )


class PlaylistItemVideo(BaseModel):
    """Complete item of a video in a playlist."""

    kind: str = Field(default="youtube#playlistItem", description="Resource type")
    etag: str = Field(description="Resource ETag")
    id: str = Field(description="Unique item ID in the playlist")
    snippet: PlaylistItemSnippet = Field(description="Video snippet information")
    contentDetails: ContentDetails = Field(description="Content details")


class PlaylistVideoResponse(BaseModel):
    """Paginated response of playlist videos with complete schemas."""

    items: list[PlaylistItemVideo] = Field(description="List of playlist items")
    total_results: int = Field(description="Total results")
    next_page_token: str | None = Field(None, description="Next page token")
    prev_page_token: str | None = Field(None, description="Previous page token")
    page_info: PageInfo = Field(description="Page information")


class DeletePlaylistVideosRequest(BaseModel):
    playlist_id: str = Field(description="Playlist ID")
    include_private_videos: bool = Field(description="Include private videos")
    include_delete_videos: bool = Field(description="Include deleted videos")
    video_ids: list[str] = Field(default=[], description="IDs of videos to delete")
