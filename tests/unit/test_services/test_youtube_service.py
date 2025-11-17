"""
Tests unitarios para YoutubeService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.application.services.youtube_service import YoutubeService
from src.schemas.youtube import (
    PaginationParams,
    DateRangeParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
)
from src.schemas.auth import SessionValidation
from src.domain.services.video_filter_service import VideoFilterService
from src.infrastructure.services.cache_service import CacheService


class TestYoutubeService:
    """Tests para YoutubeService."""

    @pytest.fixture
    def sample_session_validation(self):
        """Fixture para SessionValidation."""
        return {
            "authenticated": True,
            "user_sub": "test_user_sub",
            "session_id": "test_session_id",
            "access_token": "test_access_token",
            "token_refreshed": False,
            "new_session_token": None,
            "refresh_expires_at": int(datetime.now(timezone.utc).timestamp()) + 3600,
        }

    @pytest.fixture
    def youtube_service(self, sample_session_validation):
        """Crear instancia de YoutubeService para testing."""
        video_filter_service = VideoFilterService()
        cache_service = CacheService()
        return YoutubeService(
            session=sample_session_validation,
            video_filter_service=video_filter_service,
            cache_service=cache_service,
        )

    @pytest.fixture
    def sample_playlist_item(self):
        """Fixture para un item de playlist de ejemplo."""
        return {
            "id": "test_item_id",
            "snippet": {
                "title": "Test Video",
                "description": "Test Description",
                "publishedAt": "2020-06-15T12:00:00Z",
                "thumbnails": {},
            },
            "contentDetails": {
                "videoId": "test_video_id",
            },
        }

    @pytest.mark.asyncio
    async def test_initialize(self, youtube_service):
        """Test de inicialización."""
        # Arrange
        with patch("src.application.services.youtube_service.build") as mock_build, patch(
            "src.application.services.youtube_service.asyncio.to_thread"
        ) as mock_to_thread:
            mock_client = MagicMock()
            mock_build.return_value = mock_client
            mock_to_thread.return_value = mock_client

            # Act
            await youtube_service.initialize()

            # Assert
            assert youtube_service._youtube_client is not None
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, youtube_service):
        """Test de inicialización cuando ya está inicializado."""
        # Arrange
        mock_client = MagicMock()
        youtube_service._youtube_client = mock_client

        # Act
        await youtube_service.initialize()

        # Assert - No debe llamar a build de nuevo
        with patch("src.application.services.youtube_service.build") as mock_build:
            assert youtube_service._youtube_client is mock_client

    @pytest.mark.asyncio
    async def test_get_user_playlists_cache_hit(self, youtube_service):
        """Test de get_user_playlists con cache hit."""
        # Arrange
        await youtube_service.initialize()
        pagination = PaginationParams(max_results=25)
        
        cached_data = {
            "items": [],
            "pageInfo": {"totalResults": 0, "resultsPerPage": 25},
        }
        
        youtube_service.cache_service.get = AsyncMock(return_value=cached_data)

        # Act
        result = await youtube_service.get_user_playlists(pagination)

        # Assert
        assert isinstance(result, YoutubePlaylistListResponse)
        youtube_service.cache_service.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_playlists_cache_miss(self, youtube_service):
        """Test de get_user_playlists con cache miss."""
        # Arrange
        await youtube_service.initialize()
        pagination = PaginationParams(max_results=25)
        
        api_response = {
            "items": [],
            "pageInfo": {"totalResults": 0, "resultsPerPage": 25},
        }
        
        youtube_service.cache_service.get = AsyncMock(return_value=None)
        youtube_service.cache_service.set = AsyncMock(return_value=True)
        
        with patch(
            "src.application.services.youtube_service.asyncio.to_thread"
        ) as mock_to_thread:
            mock_to_thread.return_value = api_response

            # Act
            result = await youtube_service.get_user_playlists(pagination)

            # Assert
            assert isinstance(result, YoutubePlaylistListResponse)
            youtube_service.cache_service.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_playlists_not_initialized(self, youtube_service):
        """Test de get_user_playlists cuando no está inicializado."""
        # Arrange
        pagination = PaginationParams(max_results=25)

        # Act & Assert
        with pytest.raises(RuntimeError, match="must be initialized"):
            await youtube_service.get_user_playlists(pagination)

    @pytest.mark.asyncio
    async def test_get_playlist_videos_cache_hit(self, youtube_service, sample_playlist_item):
        """Test de get_playlist_videos con cache hit."""
        # Arrange
        await youtube_service.initialize()
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        pagination = PaginationParams(max_results=25)
        
        cached_data = {
            "items": [sample_playlist_item],
            "total_results": 1,
            "next_page_token": None,
            "prev_page_token": None,
            "page_info": {"totalResults": 1, "resultsPerPage": 25},
        }
        
        youtube_service.cache_service.get = AsyncMock(return_value=cached_data)

        # Act
        result = await youtube_service.get_playlist_videos(playlist_id, pagination)

        # Assert
        assert isinstance(result, PlaylistVideoResponse)
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_get_playlist_videos_cache_miss(self, youtube_service, sample_playlist_item):
        """Test de get_playlist_videos con cache miss."""
        # Arrange
        await youtube_service.initialize()
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        pagination = PaginationParams(max_results=25)
        
        api_response = {
            "items": [sample_playlist_item],
            "pageInfo": {"totalResults": 1, "resultsPerPage": 25},
            "nextPageToken": None,
            "prevPageToken": None,
        }
        
        youtube_service.cache_service.get = AsyncMock(return_value=None)
        youtube_service.cache_service.set = AsyncMock(return_value=True)
        
        with patch(
            "src.application.services.youtube_service.asyncio.to_thread"
        ) as mock_to_thread:
            mock_to_thread.return_value = api_response

            # Act
            result = await youtube_service.get_playlist_videos(playlist_id, pagination)

            # Assert
            assert isinstance(result, PlaylistVideoResponse)
            assert len(result.items) == 1
            youtube_service.cache_service.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_playlist_videos_by_date_ranges(
        self, youtube_service, sample_playlist_item
    ):
        """Test de get_playlist_videos_by_date_ranges."""
        # Arrange
        await youtube_service.initialize()
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        date_range = DateRangeParams(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc),
        )

        # Item dentro del rango de fechas
        item_in_range = sample_playlist_item.copy()
        item_in_range["snippet"]["publishedAt"] = "2020-06-15T12:00:00Z"

        # Item fuera del rango de fechas
        item_out_of_range = sample_playlist_item.copy()
        item_out_of_range["snippet"]["publishedAt"] = "2021-06-15T12:00:00Z"
        item_out_of_range["id"] = "item_out_of_range"

        # Mock API responses
        first_page_response = {
            "items": [item_in_range, item_out_of_range],
            "pageInfo": {"totalResults": 2, "resultsPerPage": 2},
            "nextPageToken": None,
        }

        with patch(
            "src.application.services.youtube_service.asyncio.to_thread"
        ) as mock_to_thread:
            mock_to_thread.return_value = first_page_response

            # Act
            result = await youtube_service.get_playlist_videos_by_date_ranges(
                playlist_id, date_range
            )

            # Assert
            assert isinstance(result, PlaylistVideoResponse)
            # Solo debe incluir el item dentro del rango
            assert len(result.items) == 1
            assert result.items[0]["id"] == item_in_range["id"]

    @pytest.mark.asyncio
    async def test_get_playlist_videos_by_date_ranges_multiple_pages(
        self, youtube_service, sample_playlist_item
    ):
        """Test de get_playlist_videos_by_date_ranges con múltiples páginas."""
        # Arrange
        await youtube_service.initialize()
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        date_range = DateRangeParams(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc),
        )

        item1 = sample_playlist_item.copy()
        item1["snippet"]["publishedAt"] = "2020-06-15T12:00:00Z"
        item1["id"] = "item1"

        item2 = sample_playlist_item.copy()
        item2["snippet"]["publishedAt"] = "2020-07-15T12:00:00Z"
        item2["id"] = "item2"

        # Mock API responses - primera página con nextPageToken
        first_page_response = {
            "items": [item1],
            "pageInfo": {"totalResults": 2, "resultsPerPage": 1},
            "nextPageToken": "next_token",
        }

        # Segunda página sin nextPageToken
        second_page_response = {
            "items": [item2],
            "pageInfo": {"totalResults": 2, "resultsPerPage": 1},
            "nextPageToken": None,
        }

        with patch(
            "src.application.services.youtube_service.asyncio.to_thread"
        ) as mock_to_thread:
            # Primera llamada retorna primera página, segunda retorna segunda página
            mock_to_thread.side_effect = [first_page_response, second_page_response]

            # Act
            result = await youtube_service.get_playlist_videos_by_date_ranges(
                playlist_id, date_range
            )

            # Assert
            assert isinstance(result, PlaylistVideoResponse)
            # Debe incluir ambos items
            assert len(result.items) == 2
            assert mock_to_thread.call_count == 2
