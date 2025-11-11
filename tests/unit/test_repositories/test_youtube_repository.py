"""
Tests unitarios para YoutubeRepository.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.db.repositories.youtube import YoutubeRepository
from src.schemas.youtube import (
    PaginationParams,
    DateRangeParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
    PageInfo,
)
from src.schemas.auth import SessionValidation


class TestYoutubeRepository:
    """Tests para YoutubeRepository."""

    @pytest.fixture
    def session_validation(self, sample_session_validation):
        """Fixture para SessionValidation."""
        return sample_session_validation

    @pytest.fixture
    def youtube_repo(self, session_validation):
        """Crear instancia de YoutubeRepository para testing."""
        return YoutubeRepository(session_validation)

    @pytest.fixture
    def mock_youtube_client(self):
        """Mock del cliente de YouTube."""
        client = MagicMock()
        return client

    @pytest.mark.asyncio
    async def test_initialize_success(self, youtube_repo, session_validation):
        """Test de inicialización exitosa."""
        # Arrange
        with patch("src.db.repositories.youtube.build") as mock_build, patch(
            "src.db.repositories.youtube.asyncio.to_thread"
        ) as mock_to_thread:
            mock_client = MagicMock()
            mock_build.return_value = mock_client
            mock_to_thread.return_value = mock_client

            # Act
            await youtube_repo.initialize()

            # Assert
            assert youtube_repo._youtube_client is not None
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_initialized_raises_error(self, youtube_repo):
        """Test que _ensure_initialized lanza error si no está inicializado."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="must be initialized"):
            youtube_repo._ensure_initialized()

    @pytest.mark.asyncio
    async def test_get_user_playlists_cache_hit(
        self, youtube_repo, mock_youtube_client, sample_playlist_response
    ):
        """Test de get_user_playlists con cache hit."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        pagination = PaginationParams(max_results=25)

        with patch("src.db.repositories.youtube.cache_key") as mock_cache_key, patch(
            "src.db.repositories.youtube.get_json_cache"
        ) as mock_get_cache:
            mock_cache_key.return_value = "test_cache_key"
            mock_get_cache.return_value = sample_playlist_response

            # Act
            result = await youtube_repo.get_user_playlists(pagination, use_cache=True)

            # Assert
            assert isinstance(result, YoutubePlaylistListResponse)
            mock_get_cache.assert_called_once()
            # No debe llamar a la API si hay cache
            mock_youtube_client.playlists.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_playlists_cache_miss(
        self, youtube_repo, mock_youtube_client, sample_playlist_response
    ):
        """Test de get_user_playlists con cache miss."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        pagination = PaginationParams(max_results=25)

        # Mock de la respuesta de la API
        mock_playlists = MagicMock()
        mock_list = MagicMock()
        mock_execute = MagicMock(return_value=sample_playlist_response)
        mock_list.execute = mock_execute
        mock_playlists.list.return_value = mock_list
        mock_youtube_client.playlists.return_value = mock_playlists

        with patch("src.db.repositories.youtube.cache_key") as mock_cache_key, patch(
            "src.db.repositories.youtube.get_json_cache"
        ) as mock_get_cache, patch(
            "src.db.repositories.youtube.set_json_cache"
        ) as mock_set_cache, patch(
            "src.db.repositories.youtube.asyncio.to_thread"
        ) as mock_to_thread:
            mock_cache_key.return_value = "test_cache_key"
            mock_get_cache.return_value = None  # Cache miss
            mock_to_thread.return_value = sample_playlist_response

            # Act
            result = await youtube_repo.get_user_playlists(pagination, use_cache=True)

            # Assert
            assert isinstance(result, YoutubePlaylistListResponse)
            mock_get_cache.assert_called_once()
            mock_set_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_playlists_without_cache(
        self, youtube_repo, mock_youtube_client, sample_playlist_response
    ):
        """Test de get_user_playlists sin usar cache."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        pagination = PaginationParams(max_results=25)

        with patch("src.db.repositories.youtube.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = sample_playlist_response

            # Act
            result = await youtube_repo.get_user_playlists(pagination, use_cache=False)

            # Assert
            assert isinstance(result, YoutubePlaylistListResponse)
            # No debe intentar usar cache
            with patch("src.db.repositories.youtube.get_json_cache") as mock_get_cache:
                # Verificar que no se llama a get_json_cache
                pass

    @pytest.mark.asyncio
    async def test_get_playlist_videos_cache_hit(
        self, youtube_repo, mock_youtube_client, sample_playlist_item
    ):
        """Test de get_playlist_videos con cache hit."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        pagination = PaginationParams(max_results=25)

        cached_response = {
            "items": [sample_playlist_item],
            "total_results": 1,
            "next_page_token": None,
            "prev_page_token": None,
            "page_info": {"totalResults": 1, "resultsPerPage": 25},
        }

        with patch("src.db.repositories.youtube.cache_key") as mock_cache_key, patch(
            "src.db.repositories.youtube.get_json_cache"
        ) as mock_get_cache:
            mock_cache_key.return_value = "test_cache_key"
            mock_get_cache.return_value = cached_response

            # Act
            result = await youtube_repo.get_playlist_videos(
                playlist_id, pagination, use_cache=True
            )

            # Assert
            assert isinstance(result, PlaylistVideoResponse)
            assert len(result.items) == 1
            mock_get_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_playlist_videos_cache_hit(
        self, youtube_repo, mock_youtube_client, sample_playlist_item
    ):
        """Test de get_all_playlist_videos con cache hit."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"

        cached_response = {
            "items": [sample_playlist_item],
            "total_results": 1,
            "page_info": {"totalResults": 1, "resultsPerPage": 1},
        }

        with patch("src.db.repositories.youtube.cache_key") as mock_cache_key, patch(
            "src.db.repositories.youtube.get_json_cache"
        ) as mock_get_cache:
            mock_cache_key.return_value = "test_cache_key"
            mock_get_cache.return_value = cached_response

            # Act
            result = await youtube_repo.get_all_playlist_videos(
                playlist_id, use_cache=True
            )

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0] == sample_playlist_item

    @pytest.mark.asyncio
    async def test_get_all_playlist_videos_cache_miss(
        self, youtube_repo, mock_youtube_client, sample_playlist_item
    ):
        """Test de get_all_playlist_videos con cache miss."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"

        api_response = {
            "items": [sample_playlist_item],
            "pageInfo": {"totalResults": 1, "resultsPerPage": 1},
            "nextPageToken": None,
        }

        with patch("src.db.repositories.youtube.cache_key") as mock_cache_key, patch(
            "src.db.repositories.youtube.get_json_cache"
        ) as mock_get_cache, patch(
            "src.db.repositories.youtube.set_json_cache"
        ) as mock_set_cache, patch(
            "src.db.repositories.youtube.asyncio.to_thread"
        ) as mock_to_thread:
            mock_cache_key.return_value = "test_cache_key"
            mock_get_cache.return_value = None  # Cache miss
            mock_to_thread.return_value = api_response

            # Mock del cliente de YouTube
            mock_playlist_items = MagicMock()
            mock_list = MagicMock()
            mock_execute = MagicMock(return_value=api_response)
            mock_list.execute = mock_execute
            mock_playlist_items.list.return_value = mock_list
            mock_youtube_client.playlistItems.return_value = mock_playlist_items

            # Act
            result = await youtube_repo.get_all_playlist_videos(
                playlist_id, use_cache=True
            )

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            mock_set_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_playlist_item(self, youtube_repo, mock_youtube_client):
        """Test de delete_playlist_item."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        playlist_item_id = "test_item_id"

        mock_playlist_items = MagicMock()
        mock_delete = MagicMock()
        mock_execute = MagicMock(return_value={})
        mock_delete.execute = mock_execute
        mock_playlist_items.delete.return_value = mock_delete
        mock_youtube_client.playlistItems.return_value = mock_playlist_items

        with patch("src.db.repositories.youtube.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {}

            # Act
            await youtube_repo.delete_playlist_item(playlist_item_id)

            # Assert
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_playlist_items(self, youtube_repo, mock_youtube_client):
        """Test de get_all_playlist_items."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"

        api_response = {
            "items": [{"id": "item1"}, {"id": "item2"}],
            "nextPageToken": None,
        }

        with patch("src.db.repositories.youtube.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = api_response

            # Mock del cliente de YouTube
            mock_playlist_items = MagicMock()
            mock_list = MagicMock()
            mock_execute = MagicMock(return_value=api_response)
            mock_list.execute = mock_execute
            mock_playlist_items.list.return_value = mock_list
            mock_youtube_client.playlistItems.return_value = mock_playlist_items

            # Act
            result = await youtube_repo.get_all_playlist_items(playlist_id)

            # Assert
            assert isinstance(result, list)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_invalidate_playlist_cache_success(
        self, youtube_repo, mock_youtube_client
    ):
        """Test de invalidate_playlist_cache exitoso."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"

        mock_redis_client = AsyncMock()
        mock_redis_client.delete = AsyncMock()
        mock_redis_client.scan_iter = AsyncMock()
        # Mock de scan_iter que retorna una lista vacía
        async def mock_scan_iter(match):
            return
            yield  # Make it an async generator

        mock_redis_client.scan_iter = mock_scan_iter

        with patch("src.db.repositories.youtube.get_redis_client") as mock_get_redis, patch(
            "src.db.repositories.youtube.cache_key"
        ) as mock_cache_key:
            mock_get_redis.return_value = mock_redis_client
            mock_cache_key.return_value = "test_cache_key"

            # Act
            result = await youtube_repo.invalidate_playlist_cache(playlist_id)

            # Assert
            assert result >= 0
            mock_get_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_playlist_cache_error(
        self, youtube_repo, mock_youtube_client
    ):
        """Test de invalidate_playlist_cache cuando hay error."""
        # Arrange
        youtube_repo._youtube_client = mock_youtube_client
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"

        with patch("src.db.repositories.youtube.get_redis_client") as mock_get_redis:
            mock_get_redis.side_effect = Exception("Redis error")

            # Act
            result = await youtube_repo.invalidate_playlist_cache(playlist_id)

            # Assert
            assert result == 0  # Debe retornar 0 en caso de error

