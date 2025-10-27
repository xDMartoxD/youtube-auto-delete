from src.domain.schemas.youtube import (
    PaginationParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
)

from src.db.repositories.auth import AuthRepository
from src.domain.services.google_client import GoogleClient
import logging

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


class YoutubeService:
    def __init__(
        self,
        google_client: GoogleClient,
        auth_repo: AuthRepository,
        user_sub: str,
        access_token: str,
    ):
        self.google_client = google_client
        self.auth_repo = auth_repo
        self.user_sub = user_sub
        self._youtube_client = None
        self._access_token = None
        self._initialized = False

    async def initialize(self):
        """Initialize service with valid token and YouTube client."""
        if self._initialized:
            return

        self._youtube_client = build(
            "youtube", "v3", credentials=Credentials(self._access_token)
        )
        self._initialized = True

    async def get_user_playlists(
        self, pagination: PaginationParams
    ) -> YoutubePlaylistListResponse:
        """Get user's playlists with pagination."""

        # Construir parámetros de la API
        request_params = {
            "part": "snippet,contentDetails",
            "mine": True,
            "maxResults": pagination.max_results,
        }

        # Agregar pageToken si existe
        if pagination.page_token:
            request_params["pageToken"] = pagination.page_token

        # Ejecutar request
        response: YoutubePlaylistListResponse = (
            self._youtube_client.playlists().list(**request_params).execute()
        )

        # Construir respuesta paginada
        return response

    async def get_playlist_videos(
        self, playlist_id: str, pagination: PaginationParams
    ) -> PlaylistVideoResponse:

        # Construir parámetros de la API
        request_params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": pagination.max_results,
        }

        # Agregar pageToken si existe
        if pagination.page_token:
            request_params["pageToken"] = pagination.page_token

        # Ejecutar request
        response = self._youtube_client.playlistItems().list(**request_params).execute()

        # Construir respuesta paginada
        return PlaylistVideoResponse(
            items=response.get("items", []),
            total_results=response.get("pageInfo", {}).get("totalResults", 0),
            next_page_token=response.get("nextPageToken"),
            prev_page_token=response.get("prevPageToken"),
            page_info=response.get("pageInfo", {}),
        )

    async def get_watch_later_playlist(
        self, pagination: PaginationParams
    ) -> PlaylistVideoResponse:
        """
        Get videos from the user's Watch Later playlist.
        Watch Later is a special playlist with ID 'WL'.
        """

        # Construir parámetros de la API para Watch Later
        request_params = {
            "part": "snippet,contentDetails",
            "playlistId": "WL",  # ID especial para Watch Later
            "maxResults": pagination.max_results,
        }

        # Agregar pageToken si existe
        if pagination.page_token:
            request_params["pageToken"] = pagination.page_token

        # Ejecutar request
        response = self._youtube_client.playlistItems().list(**request_params).execute()

        # Construir respuesta paginada
        return PlaylistVideoResponse(
            items=response.get("items", []),
            total_results=response.get("pageInfo", {}).get("totalResults", 0),
            next_page_token=response.get("nextPageToken"),
            prev_page_token=response.get("prevPageToken"),
            page_info=response.get("pageInfo", {}),
        )

    async def get_watch_later_info(self) -> dict:
        """
        Get information about the user's Watch Later playlist.
        Returns basic info about the playlist itself.
        """
        await self.initialize()

        # Obtener información de la playlist Watch Later
        playlist_info = (
            self._youtube_client.playlists()
            .list(
                part="snippet,contentDetails", id="WL"  # ID especial para Watch Later
            )
            .execute()
        )

        return {
            "playlist_id": "WL",
            "title": "Watch Later",
            "description": "Videos saved to watch later",
            "item_count": playlist_info.get("items", [{}])[0]
            .get("contentDetails", {})
            .get("itemCount", 0),
            "snippet": playlist_info.get("items", [{}])[0].get("snippet", {}),
        }

    async def add_to_watch_later(self, video_id: str) -> dict:
        """
        Add a video to the user's Watch Later playlist.
        """
        await self.initialize()

        # Agregar video a Watch Later
        request_body = {
            "snippet": {
                "playlistId": "WL",
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        }

        response = (
            self._youtube_client.playlistItems()
            .insert(part="snippet", body=request_body)
            .execute()
        )

        return {
            "success": True,
            "playlist_item_id": response.get("id"),
            "video_id": video_id,
            "message": "Video added to Watch Later",
        }

    async def remove_from_watch_later(self, playlist_item_id: str) -> dict:
        """
        Remove a video from the user's Watch Later playlist.
        """
        await self.initialize()

        # Eliminar video de Watch Later
        self._youtube_client.playlistItems().delete(id=playlist_item_id).execute()

        return {
            "success": True,
            "playlist_item_id": playlist_item_id,
            "message": "Video removed from Watch Later",
        }
