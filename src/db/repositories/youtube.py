"""Repository for YouTube API operations and caching."""

import asyncio
import logging
from typing import Any
from datetime import datetime, timezone

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.schemas.auth import SessionValidation
from src.schemas.youtube import (
    PaginationParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
    PageInfo,
)
from src.core.cache import get_json_cache, set_json_cache, cache_key, get_redis_client

logger = logging.getLogger(__name__)


class YoutubeRepository:
    """Repository for YouTube API operations with caching support."""

    def __init__(self, session: SessionValidation):
        self._session = session
        self._youtube_client: Any = None

    async def initialize(self):
        """
        Initialize the YouTube client in a thread to avoid blocking the event loop.
        This should be called during dependency injection before using the repository.
        """
        if self._youtube_client is None:
            # Construir el cliente en un thread para no bloquear el event loop
            credentials = Credentials(self._session["access_token"])
            self._youtube_client = await asyncio.to_thread(
                build, "youtube", "v3", credentials=credentials
            )

    def _ensure_initialized(self):
        """Ensure the YouTube client has been initialized."""
        if self._youtube_client is None:
            raise RuntimeError(
                "YoutubeRepository must be initialized before use. "
                "Call initialize() first or use the dependency injection."
            )

    async def get_user_playlists(
        self, pagination: PaginationParams, use_cache: bool = True
    ) -> YoutubePlaylistListResponse:
        """
        Get user's playlists with pagination.
        Results are cached for 30 minutes if use_cache is True.
        """
        self._ensure_initialized()

        cache_key_str = None
        # Intentar obtener del cache primero
        if use_cache:
            cache_key_str = cache_key(
                "user_playlists",
                self._session["user_sub"],
                pagination.max_results,
                pagination.page_token or "",
            )
            cached_response = await get_json_cache(cache_key_str)
            if cached_response:
                logger.debug(f"Cache hit for user playlists: {cache_key_str}")
                return YoutubePlaylistListResponse(**cached_response)

        # Cache miss - obtener de la API
        logger.debug(f"Cache miss for user playlists")

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

        # Guardar en cache (30 minutos = 1800 segundos)
        if use_cache and cache_key_str:
            response_dict = (
                response.model_dump()
                if hasattr(response, "model_dump")
                else dict(response)
            )
            await set_json_cache(cache_key_str, response_dict, expire=1800)

        return response

    async def get_playlist_videos(
        self, playlist_id: str, pagination: PaginationParams, use_cache: bool = True
    ) -> PlaylistVideoResponse:
        """
        Get videos from a playlist with pagination.
        Results are cached for 1 hour if use_cache is True.
        """
        self._ensure_initialized()

        cache_key_str = None
        # Intentar obtener del cache primero
        if use_cache:
            cache_key_str = cache_key(
                "playlist_videos",
                playlist_id,
                pagination.max_results,
                pagination.page_token or "",
            )
            cached_response = await get_json_cache(cache_key_str)
            if cached_response:
                logger.debug(f"Cache hit for playlist videos: {cache_key_str}")
                return PlaylistVideoResponse(**cached_response)

        # Cache miss - obtener de la API
        logger.debug(f"Cache miss for playlist videos")

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
        playlist_response = PlaylistVideoResponse(
            items=response.get("items", []),
            total_results=response.get("pageInfo", {}).get("totalResults", 0),
            next_page_token=response.get("nextPageToken"),
            prev_page_token=response.get("prevPageToken"),
            page_info=response.get("pageInfo", {}),
        )

        # Guardar en cache (1 hora = 3600 segundos)
        if use_cache and cache_key_str:
            response_dict = playlist_response.model_dump()
            await set_json_cache(cache_key_str, response_dict, expire=3600)

        return playlist_response

    async def get_all_playlist_videos(
        self, playlist_id: str, use_cache: bool = True
    ) -> list[dict]:
        """
        Get ALL videos from a playlist (iterates through all pages).
        Results are cached for 1 hour if use_cache is True.
        Returns raw items (dicts) for filtering.

        Strategy:
        1. First try to get from 'playlist_all_videos' cache key
        2. If not found, try to reconstruct from paginated cache entries
        3. Only if both fail, fetch from API
        """
        self._ensure_initialized()

        # Cache key para TODOS los videos de la playlist (sin filtro)
        all_videos_cache_key = cache_key("playlist_all_videos", playlist_id)

        # Intentar obtener todos los videos del cache primero
        if use_cache:
            cached_all_videos = await get_json_cache(all_videos_cache_key)
            if cached_all_videos:
                logger.debug(
                    f"Cache hit for all playlist videos: {all_videos_cache_key}"
                )
                return cached_all_videos.get("items", [])

            # Si no está en cache completo, intentar reconstruir desde cache paginado
            logger.debug(
                f"Cache miss for all playlist videos, trying to reconstruct from paginated cache"
            )
            reconstructed_items = await self._reconstruct_from_paginated_cache(
                playlist_id
            )
            if reconstructed_items:
                logger.debug(
                    f"Successfully reconstructed {len(reconstructed_items)} videos from paginated cache"
                )
                # Guardar en cache completo para próximas veces
                all_videos_response = PlaylistVideoResponse(
                    items=reconstructed_items,  # type: ignore[arg-type]
                    total_results=len(reconstructed_items),
                    next_page_token=None,
                    prev_page_token=None,
                    page_info=PageInfo(
                        totalResults=len(reconstructed_items),
                        resultsPerPage=len(reconstructed_items),
                    ),
                )
                all_videos_dict = all_videos_response.model_dump()
                await set_json_cache(all_videos_cache_key, all_videos_dict, expire=3600)
                return reconstructed_items

        # Cache miss completo - obtener TODOS los videos de la API (sin filtrar)
        logger.debug(f"Cache miss for all playlist videos, fetching from API")

        all_items = []
        next_page_token = None
        max_results_per_page = 50  # Máximo permitido por la API de YouTube
        total_results = 0
        page_info = {}

        # Iterar sobre todas las páginas para obtener TODOS los videos (sin filtrar)
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

            # Obtener items de esta página (SIN filtrar)
            page_items = response.get("items", [])
            all_items.extend(page_items)

            # Guardar info de la página (usamos la última respuesta)
            page_info = response.get("pageInfo", {})
            total_results = page_info.get("totalResults", len(all_items))

            # Obtener token de siguiente página
            next_page_token = response.get("nextPageToken")

            # Si no hay más páginas, salir del loop
            if not next_page_token:
                break

        # Guardar TODOS los videos en cache (sin filtrar)
        if use_cache:
            all_videos_response = PlaylistVideoResponse(
                items=all_items,  # type: ignore[arg-type]
                total_results=total_results,
                next_page_token=None,
                prev_page_token=None,
                page_info=page_info,
            )
            all_videos_dict = all_videos_response.model_dump()
            await set_json_cache(all_videos_cache_key, all_videos_dict, expire=3600)
            logger.debug(f"Cached {len(all_items)} videos for playlist {playlist_id}")

        return all_items

    async def _reconstruct_from_paginated_cache(
        self, playlist_id: str
    ) -> list[dict] | None:
        """
        Intenta reconstruir todos los videos de una playlist desde el cache paginado.

        Busca todas las claves que coincidan con 'playlist_videos:{playlist_id}:*'
        y reconstruye la lista completa de videos.

        Returns:
            Lista de items si se puede reconstruir, None si no hay suficiente cache.
        """
        try:
            client = await get_redis_client()
            pattern = f"playlist_videos:{playlist_id}:*"

            all_items = []
            cache_keys_found = []

            # Buscar todas las claves que coincidan con el patrón
            async for key in client.scan_iter(match=pattern):
                cache_keys_found.append(key)
                cached_data = await get_json_cache(key)
                if cached_data and isinstance(cached_data, dict):
                    items = cached_data.get("items", [])
                    if items:
                        all_items.extend(items)

            if not cache_keys_found:
                logger.debug(f"No paginated cache found for playlist {playlist_id}")
                return None

            if not all_items:
                logger.debug(
                    f"Found {len(cache_keys_found)} cache keys but no items for playlist {playlist_id}"
                )
                return None

            # Eliminar duplicados basándose en el 'id' del item
            seen_ids = set()
            unique_items = []
            for item in all_items:
                item_id = item.get("id") if isinstance(item, dict) else None
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    unique_items.append(item)

            logger.debug(
                f"Reconstructed {len(unique_items)} unique videos from {len(cache_keys_found)} cache entries"
            )

            # Solo retornar si tenemos una cantidad razonable de items
            # (para evitar retornar cache parcial que podría ser incompleto)
            if len(unique_items) > 0:
                return unique_items

            return None
        except Exception as e:
            logger.warning(
                f"Error reconstructing from paginated cache for playlist {playlist_id}: {e}"
            )
            return None

    async def delete_playlist_item(self, playlist_item_id: str) -> None:
        """Delete a playlist item by its ID."""
        self._ensure_initialized()

        def _delete_item():
            return (
                self._youtube_client.playlistItems()
                .delete(id=playlist_item_id)
                .execute()
            )

        await asyncio.to_thread(_delete_item)

    async def get_all_playlist_items(self, playlist_id: str) -> list[dict]:
        """
        Get ALL playlist items (for finding private videos, etc.).
        Does not use cache - always fetches fresh data.
        """
        self._ensure_initialized()

        all_playlist_items = []
        next_page_token = None
        max_results_per_page = 50

        # Iterar sobre todas las páginas para obtener todos los items
        while True:
            request_params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": max_results_per_page,
            }

            if next_page_token:
                request_params["pageToken"] = next_page_token

            def _execute_request():
                return (
                    self._youtube_client.playlistItems()
                    .list(**request_params)
                    .execute()
                )

            response = await asyncio.to_thread(_execute_request)
            page_items = response.get("items", [])
            all_playlist_items.extend(page_items)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return all_playlist_items

    async def invalidate_playlist_cache(self, playlist_id: str) -> int:
        """
        Invalidate all cache entries for a playlist.
        Returns the number of cache entries invalidated.
        """
        try:
            client = await get_redis_client()
            deleted_count = 0

            # Invalidar cache de todos los videos de la playlist
            all_videos_key = cache_key("playlist_all_videos", playlist_id)
            await client.delete(all_videos_key)
            deleted_count += 1

            # Invalidar caches de videos paginados
            pattern1 = f"playlist_videos:{playlist_id}*"
            async for key in client.scan_iter(match=pattern1):
                await client.delete(key)
                deleted_count += 1

            if deleted_count > 0:
                logger.debug(
                    f"Invalidated {deleted_count} cache entries for playlist {playlist_id}"
                )
            return deleted_count
        except Exception as e:
            logger.warning(f"Error invalidating cache for playlist {playlist_id}: {e}")
            return 0
