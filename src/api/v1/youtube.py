from typing import Annotated
from fastapi import APIRouter, Depends, Query, status, HTTPException
from src.schemas.youtube import (
    PaginationParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
)
from src.services.youtube import YoutubeService
from src.api.deps import get_youtube_service, youtube_service_dependency

router = APIRouter()


@router.get("/playlists", status_code=status.HTTP_200_OK)
async def get_user_playlists(
    pagination_query: Annotated[PaginationParams, Query()],
    youtube_service: youtube_service_dependency,
) -> YoutubePlaylistListResponse:
    """Get user's YouTube playlists with pagination."""
    playlists = await youtube_service.get_user_playlists(pagination_query)
    return playlists


@router.get(
    "/watch-later", status_code=status.HTTP_200_OK, response_model=PlaylistVideoResponse
)
async def get_watch_later_playlist(
    pagination_query: Annotated[PaginationParams, Query()],
    youtube_service: youtube_service_dependency,
) -> PlaylistVideoResponse:
    """
    Get user's Watch Later playlist with pagination.

    - **max_results**: Número máximo de resultados por página (1-50)
    - **page_token**: Token de página para navegación
    """
    return await youtube_service.get_watch_later_playlist(pagination_query)


@router.get("/watch-later/info", status_code=status.HTTP_200_OK)
async def get_watch_later_info(
    youtube_service: youtube_service_dependency,
) -> dict:
    """Get information about the user's Watch Later playlist."""
    return await youtube_service.get_watch_later_info()


@router.post("/watch-later/add/{video_id}", status_code=status.HTTP_201_CREATED)
async def add_to_watch_later(
    video_id: str,
    youtube_service: youtube_service_dependency,
) -> dict:
    """
    Add a video to the user's Watch Later playlist.

    - **video_id**: ID del video de YouTube a agregar
    """
    try:
        return await youtube_service.add_to_watch_later(video_id)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to add video to Watch Later: {str(e)}"
        )


@router.delete("/watch-later/remove/{playlist_item_id}", status_code=status.HTTP_200_OK)
async def remove_from_watch_later(
    playlist_item_id: str,
    youtube_service: youtube_service_dependency,
) -> dict:
    """
    Remove a video from the user's Watch Later playlist.

    - **playlist_item_id**: ID del item en la playlist (no el video_id)
    """
    try:
        return await youtube_service.remove_from_watch_later(playlist_item_id)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to remove video from Watch Later: {str(e)}"
        )
