"""Application service for YouTube - orchestrates domain and infrastructure."""

from typing import Any
import asyncio
import logging

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.schemas.auth import SessionValidation
from src.schemas.youtube import (
    PaginationParams,
    DateRangeParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
)
from src.domain.services.video_filter_service import VideoFilterService
from src.infrastructure.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class YoutubeService:
    """
    Application service - orchestrates domain and infrastructure.
    NO contiene lógica de negocio, solo orquesta.
    """

    def __init__(
        self,
        session: SessionValidation,
        video_filter_service: VideoFilterService | None = None,
        cache_service: CacheService | None = None,
    ):
        self._session = session
        self._youtube_client: Any = None
        self.video_filter_service = video_filter_service or VideoFilterService()
        self.cache_service = cache_service or CacheService()
        self._user_id = session.get("user_sub")

    def _ensure_initialized(self) -> None:
        """Ensure the YouTube client has been initialized."""
        if self._youtube_client is None:
            raise RuntimeError(
                "YoutubeService must be initialized before use. "
                "Call initialize() first or use the dependency injection."
            )

    async def initialize(self) -> None:
        """
        Initialize the YouTube client in a thread to avoid blocking the event loop.
        This should be called during dependency injection before using the service.
        """
        if self._youtube_client is None:
            # INFRAESTRUCTURA: Construir el cliente en un thread para no bloquear el event loop
            credentials = Credentials(self._session["access_token"])
            self._youtube_client = await asyncio.to_thread(
                build, "youtube", "v3", credentials=credentials
            )

    async def get_user_playlists(
        self, pagination: PaginationParams
    ) -> YoutubePlaylistListResponse:
        """Get user's playlists with pagination."""
        self._ensure_initialized()

        async def _fetch_playlists() -> YoutubePlaylistListResponse:
            """Fetch playlists from YouTube API."""
            # INFRAESTRUCTURA: Construir parámetros de la API
            request_params = {
                "part": "snippet,contentDetails",
                "mine": True,
                "maxResults": pagination.max_results,
            }

            # Agregar pageToken si existe
            if pagination.page_token:
                request_params["pageToken"] = pagination.page_token

            # INFRAESTRUCTURA: Ejecutar request en un thread para no bloquear el event loop
            def _execute_request():
                return self._youtube_client.playlists().list(**request_params).execute()

            response_dict = await asyncio.to_thread(_execute_request)

            # Convertir dict a modelo Pydantic
            return YoutubePlaylistListResponse(**response_dict)

        # INFRAESTRUCTURA: Get from cache or fetch
        cached_result = await self.cache_service.get(
            "user_playlists",
            user_id=self._user_id,
            max_results=pagination.max_results,
            page_token=pagination.page_token or "",
        )

        if cached_result:
            return YoutubePlaylistListResponse(**cached_result)

        # Cache miss - fetch and cache
        response = await _fetch_playlists()
        await self.cache_service.set(
            "user_playlists",
            response.model_dump(),
            expire=1800,  # 30 minutos
            user_id=self._user_id,
            max_results=pagination.max_results,
            page_token=pagination.page_token or "",
        )

        return response

    async def get_playlist_videos(
        self, playlist_id: str, pagination: PaginationParams
    ) -> PlaylistVideoResponse:
        """Get videos from a playlist with pagination."""
        self._ensure_initialized()

        async def _fetch_videos() -> PlaylistVideoResponse:
            """Fetch videos from YouTube API."""
            # INFRAESTRUCTURA: Construir parámetros de la API
            request_params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": pagination.max_results,
            }

            # Agregar pageToken si existe
            if pagination.page_token:
                request_params["pageToken"] = pagination.page_token

            # INFRAESTRUCTURA: Ejecutar request en un thread para no bloquear el event loop
            def _execute_request():
                return (
                    self._youtube_client.playlistItems()
                    .list(**request_params)
                    .execute()
                )

            response = await asyncio.to_thread(_execute_request)

            # Construir respuesta paginada
            return PlaylistVideoResponse(
                items=response.get("items", []),
                total_results=response.get("pageInfo", {}).get("totalResults", 0),
                next_page_token=response.get("nextPageToken"),
                prev_page_token=response.get("prevPageToken"),
                page_info=response.get("pageInfo", {}),
            )

        # INFRAESTRUCTURA: Get from cache or fetch
        cached_result = await self.cache_service.get(
            "playlist_videos",
            playlist_id=playlist_id,
            max_results=pagination.max_results,
            page_token=pagination.page_token or "",
        )

        if cached_result:
            return PlaylistVideoResponse(**cached_result)

        # Cache miss - fetch and cache
        result = await _fetch_videos()
        await self.cache_service.set(
            "playlist_videos",
            result.model_dump(),
            expire=3600,  # 1 hora
            playlist_id=playlist_id,
            max_results=pagination.max_results,
            page_token=pagination.page_token or "",
        )

        return result

    async def get_playlist_videos_by_date_ranges(
        self,
        playlist_id: str,
        date_range: DateRangeParams,
    ) -> PlaylistVideoResponse:
        """
        Obtiene TODOS los videos de una playlist dentro de un rango de fechas.
        Itera sobre todas las páginas para obtener todos los resultados que coincidan con el filtro.
        """
        self._ensure_initialized()

        all_items = []
        next_page_token = None
        max_results_per_page = 50  # Máximo permitido por la API de YouTube

        # Iterar sobre todas las páginas para obtener todos los videos
        while True:
            # INFRAESTRUCTURA: Construir parámetros de la API
            request_params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": max_results_per_page,
            }

            # Agregar pageToken si existe
            if next_page_token:
                request_params["pageToken"] = next_page_token

            # INFRAESTRUCTURA: Ejecutar request en un thread para no bloquear el event loop
            def _execute_request():
                return (
                    self._youtube_client.playlistItems()
                    .list(**request_params)
                    .execute()
                )

            response = await asyncio.to_thread(_execute_request)

            # Obtener items de esta página
            page_items = response.get("items", [])

            # DOMINIO: Filtrar items por rango de fechas usando servicio de dominio
            filtered_items = self.video_filter_service.filter_by_date_range(
                page_items, date_range.date_from, date_range.date_to
            )
            all_items.extend(filtered_items)

            # Obtener token de siguiente página
            next_page_token = response.get("nextPageToken")

            # Si no hay más páginas, salir del loop
            if not next_page_token:
                break

        # Obtener información de la página (usamos la última respuesta)
        page_info = response.get("pageInfo", {})

        # Construir respuesta con todos los items filtrados
        return PlaylistVideoResponse(
            items=all_items,
            total_results=len(all_items),
            next_page_token=None,  # Ya obtuvimos todos los resultados
            prev_page_token=None,
            page_info=page_info,
        )
