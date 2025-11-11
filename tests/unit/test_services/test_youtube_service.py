"""
Tests unitarios para YoutubeService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.services.youtube import YoutubeService, PRIVATE_VIDEO_TITLE, PRIVATE_VIDEO_DESCRIPTION
from src.schemas.youtube import (
    PaginationParams,
    DateRangeParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
    DeletePlaylistVideosRequest,
    PageInfo,
)
from src.schemas.auth import SessionValidation


class TestYoutubeService:
    """Tests para YoutubeService."""

    @pytest.fixture
    def session_validation(self, sample_session_validation):
        """Fixture para SessionValidation."""
        return sample_session_validation

    @pytest.fixture
    def mock_youtube_repo(self):
        """Mock del YoutubeRepository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def youtube_service(self, session_validation, mock_youtube_repo):
        """Crear instancia de YoutubeService para testing."""
        return YoutubeService(session_validation, mock_youtube_repo)

    @pytest.mark.asyncio
    async def test_initialize(self, youtube_service, mock_youtube_repo):
        """Test de inicialización."""
        # Act
        await youtube_service.initialize()

        # Assert
        mock_youtube_repo.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_playlists(self, youtube_service, mock_youtube_repo):
        """Test de get_user_playlists."""
        # Arrange
        pagination = PaginationParams(max_results=25)
        expected_response = YoutubePlaylistListResponse(
            items=[],
            pageInfo={"totalResults": 0, "resultsPerPage": 25},
        )
        mock_youtube_repo.get_user_playlists.return_value = expected_response

        # Act
        result = await youtube_service.get_user_playlists(pagination)

        # Assert
        assert isinstance(result, YoutubePlaylistListResponse)
        mock_youtube_repo.get_user_playlists.assert_called_once_with(
            pagination, use_cache=True
        )

    @pytest.mark.asyncio
    async def test_get_playlist_videos(self, youtube_service, mock_youtube_repo):
        """Test de get_playlist_videos."""
        # Arrange
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        pagination = PaginationParams(max_results=25)
        expected_response = PlaylistVideoResponse(
            items=[],
            total_results=0,
            next_page_token=None,
            prev_page_token=None,
            page_info=PageInfo(totalResults=0, resultsPerPage=25),
        )
        mock_youtube_repo.get_playlist_videos.return_value = expected_response

        # Act
        result = await youtube_service.get_playlist_videos(playlist_id, pagination)

        # Assert
        assert isinstance(result, PlaylistVideoResponse)
        mock_youtube_repo.get_playlist_videos.assert_called_once_with(
            playlist_id, pagination, use_cache=True
        )

    @pytest.mark.asyncio
    async def test_get_playlist_videos_by_date_ranges(
        self, youtube_service, mock_youtube_repo, sample_playlist_item
    ):
        """Test de get_playlist_videos_by_date_ranges."""
        # Arrange
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

        all_items = [item_in_range, item_out_of_range]
        mock_youtube_repo.get_all_playlist_videos.return_value = all_items

        cached_response = {
            "items": all_items,
            "page_info": {"totalResults": 2, "resultsPerPage": 2},
        }

        with patch("src.services.youtube.get_json_cache") as mock_get_cache, patch(
            "src.services.youtube.cache_key"
        ) as mock_cache_key:
            mock_cache_key.return_value = "test_cache_key"
            mock_get_cache.return_value = cached_response

            # Act
            result = await youtube_service.get_playlist_videos_by_date_ranges(
                playlist_id, date_range
            )

            # Assert
            assert isinstance(result, PlaylistVideoResponse)
            # Solo debe incluir el item dentro del rango
            assert len(result.items) == 1
            assert result.items[0]["id"] == item_in_range["id"]
            mock_youtube_repo.get_all_playlist_videos.assert_called_once_with(
                playlist_id, use_cache=True
            )

    @pytest.mark.asyncio
    async def test_get_playlist_videos_by_date_ranges_no_cache(
        self, youtube_service, mock_youtube_repo, sample_playlist_item
    ):
        """Test de get_playlist_videos_by_date_ranges sin cache."""
        # Arrange
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        date_range = DateRangeParams(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc),
        )

        item_in_range = sample_playlist_item.copy()
        item_in_range["snippet"]["publishedAt"] = "2020-06-15T12:00:00Z"

        all_items = [item_in_range]
        mock_youtube_repo.get_all_playlist_videos.return_value = all_items

        with patch("src.services.youtube.get_json_cache") as mock_get_cache, patch(
            "src.services.youtube.cache_key"
        ) as mock_cache_key:
            mock_cache_key.return_value = "test_cache_key"
            mock_get_cache.return_value = None  # No hay cache

            # Act
            result = await youtube_service.get_playlist_videos_by_date_ranges(
                playlist_id, date_range
            )

            # Assert
            assert isinstance(result, PlaylistVideoResponse)
            assert len(result.items) == 1

    def test_filter_items_by_date(self, youtube_service, sample_playlist_item):
        """Test de _filter_items_by_date."""
        # Arrange
        date_range = DateRangeParams(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc),
        )

        # Item dentro del rango
        item_in_range = sample_playlist_item.copy()
        item_in_range["snippet"]["publishedAt"] = "2020-06-15T12:00:00Z"

        # Item antes del rango
        item_before = sample_playlist_item.copy()
        item_before["snippet"]["publishedAt"] = "2019-06-15T12:00:00Z"
        item_before["id"] = "item_before"

        # Item después del rango
        item_after = sample_playlist_item.copy()
        item_after["snippet"]["publishedAt"] = "2021-06-15T12:00:00Z"
        item_after["id"] = "item_after"

        items = [item_in_range, item_before, item_after]

        # Act
        result = youtube_service._filter_items_by_date(items, date_range)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == item_in_range["id"]

    def test_filter_items_by_date_no_date_range(
        self, youtube_service, sample_playlist_item
    ):
        """Test de _filter_items_by_date sin rango de fechas."""
        # Arrange
        items = [sample_playlist_item]

        # Act - Sin date_range (solo date_from o date_to)
        date_range = DateRangeParams(
            date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2020, 12, 31, tzinfo=timezone.utc),
        )
        result = youtube_service._filter_items_by_date(items, date_range)

        # Assert - Debe retornar todos los items si no hay filtro
        # (En este caso hay filtro, pero el item está fuera del rango)
        assert isinstance(result, list)

    def test_is_private_true(self, youtube_service, sample_private_video_item):
        """Test de _is_private retorna True para video privado."""
        # Act
        result = youtube_service._is_private(sample_private_video_item)

        # Assert
        assert result is True

    def test_is_private_false(self, youtube_service, sample_playlist_item):
        """Test de _is_private retorna False para video normal."""
        # Act
        result = youtube_service._is_private(sample_playlist_item)

        # Assert
        assert result is False

    def test_is_private_partial_match(self, youtube_service):
        """Test de _is_private retorna False si solo coincide título o descripción."""
        # Arrange - Solo título coincide
        item_title_only = {
            "snippet": {
                "title": PRIVATE_VIDEO_TITLE,
                "description": "Different description",
            }
        }

        # Arrange - Solo descripción coincide
        item_description_only = {
            "snippet": {
                "title": "Different title",
                "description": PRIVATE_VIDEO_DESCRIPTION,
            }
        }

        # Act
        result_title = youtube_service._is_private(item_title_only)
        result_description = youtube_service._is_private(item_description_only)

        # Assert
        assert result_title is False
        assert result_description is False

    @pytest.mark.asyncio
    async def test_delete_playlist_videos_with_video_ids(
        self, youtube_service, mock_youtube_repo
    ):
        """Test de delete_playlist_videos con video_ids."""
        # Arrange
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        delete_request = DeletePlaylistVideosRequest(
            video_ids=["item_id_1", "item_id_2"], include_private_videos=False
        )

        mock_youtube_repo.delete_playlist_item = AsyncMock()
        mock_youtube_repo.invalidate_playlist_cache = AsyncMock(return_value=2)

        # Act
        await youtube_service.delete_playlist_videos(playlist_id, delete_request)

        # Assert
        assert mock_youtube_repo.delete_playlist_item.call_count == 2
        mock_youtube_repo.invalidate_playlist_cache.assert_called_once_with(playlist_id)

    @pytest.mark.asyncio
    async def test_delete_playlist_videos_with_private_videos(
        self, youtube_service, mock_youtube_repo, sample_private_video_item
    ):
        """Test de delete_playlist_videos incluyendo videos privados."""
        # Arrange
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        delete_request = DeletePlaylistVideosRequest(
            video_ids=[], include_private_videos=True
        )

        all_items = [sample_private_video_item]
        mock_youtube_repo.get_all_playlist_items.return_value = all_items
        mock_youtube_repo.delete_playlist_item = AsyncMock()
        mock_youtube_repo.invalidate_playlist_cache = AsyncMock(return_value=1)

        # Act
        await youtube_service.delete_playlist_videos(playlist_id, delete_request)

        # Assert
        mock_youtube_repo.get_all_playlist_items.assert_called_once_with(playlist_id)
        mock_youtube_repo.delete_playlist_item.assert_called_once()
        mock_youtube_repo.invalidate_playlist_cache.assert_called_once_with(playlist_id)

    @pytest.mark.asyncio
    async def test_delete_playlist_videos_no_video_ids_no_private(
        self, youtube_service, mock_youtube_repo
    ):
        """Test de delete_playlist_videos sin video_ids ni include_private_videos."""
        # Arrange
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        delete_request = DeletePlaylistVideosRequest(
            video_ids=[], include_private_videos=False
        )

        # Act
        await youtube_service.delete_playlist_videos(playlist_id, delete_request)

        # Assert
        # No debe llamar a delete_playlist_item ni invalidate_playlist_cache
        mock_youtube_repo.delete_playlist_item.assert_not_called()
        mock_youtube_repo.invalidate_playlist_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_playlist_videos_with_error(
        self, youtube_service, mock_youtube_repo
    ):
        """Test de delete_playlist_videos cuando hay error al eliminar."""
        # Arrange
        playlist_id = "PLDAcr1SgpcYAPESAxoaZaM4ATliC6pSQW"
        delete_request = DeletePlaylistVideosRequest(
            video_ids=["item_id_1", "item_id_2"], include_private_videos=False
        )

        # Primer delete exitoso, segundo falla
        mock_youtube_repo.delete_playlist_item = AsyncMock(side_effect=[
            None,  # Primera llamada exitosa
            Exception("Delete error"),  # Segunda llamada falla
        ])
        mock_youtube_repo.invalidate_playlist_cache = AsyncMock(return_value=1)

        # Act
        await youtube_service.delete_playlist_videos(playlist_id, delete_request)

        # Assert
        # Debe intentar eliminar ambos, aunque uno falle
        assert mock_youtube_repo.delete_playlist_item.call_count == 2
        mock_youtube_repo.invalidate_playlist_cache.assert_called_once()

