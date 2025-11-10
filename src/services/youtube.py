from typing import Any
import asyncio
from src.schemas.auth import SessionValidation
from src.schemas.youtube import (
    PaginationParams,
    DateRangeParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
)


import logging

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


class YoutubeService:
    def __init__(
        self,
        session: SessionValidation,
    ):
        self._session = session
        self._youtube_client: Any = None

    def _ensure_initialized(self):
        """Ensure the YouTube client has been initialized."""
        if self._youtube_client is None:
            raise RuntimeError(
                "YoutubeService must be initialized before use. "
                "Call initialize() first or use the dependency injection."
            )

    async def initialize(self):
        """
        Initialize the YouTube client in a thread to avoid blocking the event loop.
        This should be called during dependency injection before using the service.
        """
        if self._youtube_client is None:
            # Construir el cliente en un thread para no bloquear el event loop
            credentials = Credentials(self._session["access_token"])
            self._youtube_client = await asyncio.to_thread(
                build, "youtube", "v3", credentials=credentials
            )

    async def get_user_playlists(
        self, pagination: PaginationParams
    ) -> YoutubePlaylistListResponse:
        """Get user's playlists with pagination."""
        self._ensure_initialized()

        # Construir parámetros de la API
        request_params = {
            "part": "snippet,contentDetails",
            "mine": True,
            "maxResults": pagination.max_results,
        }

        # Agregar pageToken si existe
        if pagination.page_token:
            request_params["pageToken"] = pagination.page_token

        # Ejecutar request en un thread para no bloquear el event loop
        def _execute_request():
            return self._youtube_client.playlists().list(**request_params).execute()

        response: YoutubePlaylistListResponse = await asyncio.to_thread(
            _execute_request
        )

        # Construir respuesta paginada
        return response

    async def get_playlist_videos(
        self, playlist_id: str, pagination: PaginationParams
    ) -> PlaylistVideoResponse:
        self._ensure_initialized()

        # Construir parámetros de la API
        request_params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": pagination.max_results,
        }

        # Agregar pageToken si existe
        if pagination.page_token:
            request_params["pageToken"] = pagination.page_token

        # Ejecutar request en un thread para no bloquear el event loop
        def _execute_request():
            return self._youtube_client.playlistItems().list(**request_params).execute()

        response = await asyncio.to_thread(_execute_request)

        # Construir respuesta paginada
        return PlaylistVideoResponse(
            items=response.get("items", []),
            total_results=response.get("pageInfo", {}).get("totalResults", 0),
            next_page_token=response.get("nextPageToken"),
            prev_page_token=response.get("prevPageToken"),
            page_info=response.get("pageInfo", {}),
        )

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
            # Construir parámetros de la API
            request_params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": max_results_per_page,
            }

            # Agregar pageToken si existe
            if next_page_token:
                request_params["pageToken"] = next_page_token

            # Ejecutar request en un thread para no bloquear el event loop
            def _execute_request():
                return (
                    self._youtube_client.playlistItems()
                    .list(**request_params)
                    .execute()
                )

            response = await asyncio.to_thread(_execute_request)

            # Obtener items de esta página
            page_items = response.get("items", [])

            # Filtrar items por rango de fechas
            filtered_items = self._filter_items_by_date(page_items, date_range)
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

    def _filter_items_by_date(
        self, items: list[dict], date_range: DateRangeParams
    ) -> list[dict]:
        """
        Filtra items de playlist por rango de fechas.
        Filtra por fecha de agregado a la playlist (snippet.publishedAt).
        """
        from datetime import datetime, timezone

        filtered_items = []

        for item in items:
            include_item = True

            # Filtrar por fecha de agregado a la playlist (snippet.publishedAt)
            if date_range.date_from or date_range.date_to:
                snippet = item.get("snippet", {})
                published_at_str = snippet.get("publishedAt")

                if published_at_str:
                    # Parsear fecha ISO 8601
                    published_at = datetime.fromisoformat(
                        published_at_str.replace("Z", "+00:00")
                    )

                    if date_range.date_from:
                        date_from_utc = date_range.date_from
                        if date_from_utc.tzinfo is None:
                            date_from_utc = date_from_utc.replace(tzinfo=timezone.utc)
                        if published_at < date_from_utc:
                            include_item = False

                    if include_item and date_range.date_to:
                        date_to_utc = date_range.date_to
                        if date_to_utc.tzinfo is None:
                            date_to_utc = date_to_utc.replace(tzinfo=timezone.utc)
                        if published_at > date_to_utc:
                            include_item = False
                else:
                    # Si no tiene fecha de publicación, excluir el item
                    include_item = False

            if include_item:
                filtered_items.append(item)

        return filtered_items
