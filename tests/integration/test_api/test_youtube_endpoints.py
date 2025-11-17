"""
Integration tests for YouTube API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from src.schemas.youtube import (
    YoutubePlaylistListResponse,
    PlaylistVideoResponse,
    DateRangeParams,
)


class TestYoutubeEndpoints:
    """Integration tests for YouTube endpoints."""

    def test_get_user_playlists_requires_authentication(self, client: TestClient):
        """Test that get_user_playlists requires authentication."""
        # Act
        response = client.get("/api/youtube/playlists")

        # Assert
        assert response.status_code in [401, 422]  # Unauthorized or validation error

    def test_get_playlist_videos_requires_authentication(self, client: TestClient):
        """Test that get_playlist_videos requires authentication."""
        # Act
        response = client.get("/api/youtube/playlists/test_playlist_id/videos")

        # Assert
        assert response.status_code in [401, 422]  # Unauthorized or validation error

    def test_get_playlist_videos_with_invalid_playlist_id(self, client: TestClient):
        """Test get_playlist_videos with invalid playlist ID format."""
        # Act
        response = client.get("/api/youtube/playlists/invalid/videos")

        # Assert
        # Should fail authentication first, but if authenticated, would validate playlist_id
        assert response.status_code in [401, 422, 400]

    def test_delete_playlist_videos_requires_authentication(self, client: TestClient):
        """Test that delete_playlist_videos requires authentication."""
        # Arrange
        request_data = {
            "video_ids": ["video1", "video2"],
            "include_private_videos": False
        }

        # Act
        response = client.post(
            "/api/youtube/playlists/test_playlist_id/delete",
            json=request_data
        )

        # Assert
        assert response.status_code in [401, 422]  # Unauthorized or validation error

    def test_get_playlist_videos_with_pagination_params(self, client: TestClient):
        """Test get_playlist_videos with pagination parameters."""
        # Act
        response = client.get(
            "/api/youtube/playlists/test_playlist_id/videos?max_results=10&page_token=test_token"
        )

        # Assert
        # Should fail authentication, but validates query params
        assert response.status_code in [401, 422]

    def test_get_playlist_videos_with_date_range_params(self, client: TestClient):
        """Test get_playlist_videos with date range parameters."""
        # Arrange
        date_from = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        date_to = datetime(2020, 12, 31, tzinfo=timezone.utc).isoformat()

        # Act
        response = client.get(
            f"/api/youtube/playlists/test_playlist_id/videos?date_from={date_from}&date_to={date_to}"
        )

        # Assert
        # Should fail authentication, but validates query params
        assert response.status_code in [401, 422]

    def test_get_playlist_videos_invalid_date_range(self, client: TestClient):
        """Test get_playlist_videos with invalid date range."""
        # Arrange
        date_from = datetime(2020, 12, 31, tzinfo=timezone.utc).isoformat()
        date_to = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()  # Invalid: to < from

        # Act
        response = client.get(
            f"/api/youtube/playlists/test_playlist_id/videos?date_from={date_from}&date_to={date_to}"
        )

        # Assert
        # Should fail validation
        assert response.status_code in [400, 422]

