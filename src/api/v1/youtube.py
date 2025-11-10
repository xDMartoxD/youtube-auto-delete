from typing import Annotated
from fastapi import APIRouter, Body, Depends, Query, status
from src.schemas.youtube import (
    DeletePlaylistVideosRequest,
    PaginationParams,
    PlaylistVideoQueryParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
)
from src.api.deps import current_session_dependency, youtube_service_dependency
from src.api.utils import get_pagination_params, get_playlist_video_query_params

router = APIRouter()


@router.get("/playlists", status_code=status.HTTP_200_OK)
async def get_user_playlists(
    youtube_service: youtube_service_dependency,
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
) -> YoutubePlaylistListResponse:
    """Get user's YouTube playlists with pagination."""
    playlists = await youtube_service.get_user_playlists(pagination)
    return playlists


@router.get("/playlists/{playlist_id}/videos", status_code=status.HTTP_200_OK)
async def get_playlist_videos(
    playlist_id: str,
    youtube_service: youtube_service_dependency,
    query_params: Annotated[
        PlaylistVideoQueryParams, Depends(get_playlist_video_query_params)
    ],
) -> PlaylistVideoResponse:
    """
    Get videos from a YouTube playlist with pagination and optional date filtering.

    - **max_results**: Número máximo de resultados por página (1-50)
    - **page_token**: Token de página para paginación
    - **date_from**: Filtrar videos agregados a la playlist desde esta fecha (ISO 8601)
    - **date_to**: Filtrar videos agregados a la playlist hasta esta fecha (ISO 8601)
    """
    pagination = query_params.pagination
    date_range = query_params.date_range

    if date_range:
        videos = await youtube_service.get_playlist_videos_by_date_ranges(
            playlist_id,
            date_range,
        )
    else:
        videos = await youtube_service.get_playlist_videos(
            playlist_id,
            pagination,
        )

    return videos


@router.post("/playlists/{playlist_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist_videos(
    playlist_id: str,
    request: Annotated[
        DeletePlaylistVideosRequest, Body(media_type="application/json")
    ],
    youtube_service: youtube_service_dependency,
    session: current_session_dependency,
) -> None:
    pass
