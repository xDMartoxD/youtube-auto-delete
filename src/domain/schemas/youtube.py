from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Parámetros de paginación para YouTube API."""

    max_results: int = Field(
        25, ge=1, le=50, description="Número máximo de resultados por página"
    )
    page_token: str | None = Field(None, description="Token de página para paginación")

    model_config = {"extra": "forbid"}


from pydantic import BaseModel, Field
from typing import List, Optional, Any


class PageInfo(BaseModel):
    totalResults: int
    resultsPerPage: int


class PlaylistSnippet(BaseModel):
    title: str
    description: Optional[str] = None
    publishedAt: Optional[str] = None
    channelId: Optional[str] = None
    channelTitle: Optional[str] = None
    thumbnails: Optional[dict[str, Any]] = None


class PlaylistItem(BaseModel):
    kind: str
    etag: str
    id: str
    snippet: Optional[PlaylistSnippet] = None


class YoutubePlaylistListResponse(BaseModel):
    kind: str = Field(..., example="youtube#playlistListResponse")
    etag: str
    nextPageToken: str | None = None
    pageInfo: PageInfo
    items: List[PlaylistItem]


class PlaylistVideoResponse(BaseModel):
    """Respuesta paginada de videos de playlist."""

    items: list[dict]
    total_results: int
    next_page_token: Optional[str] = None
    prev_page_token: Optional[str] = None
    page_info: dict
