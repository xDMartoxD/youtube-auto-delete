"""
Integration tests for the multi-provider playlist endpoints, using mock providers.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from src.api.deps import _get_google_client, get_playlist_management_service
from src.application.services.playlist_management_service import (
    PlaylistManagementService,
)
from src.domain.providers import ProviderType
from src.infrastructure.providers.mock_provider import (
    MockPlaylistProvider,
    reset_mock_libraries,
)

BASE = "/v1/providers/spotify/playlists"


@pytest.fixture
def client(app) -> TestClient:
    reset_mock_libraries()

    def override():
        yield PlaylistManagementService(
            {ProviderType.SPOTIFY: MockPlaylistProvider(ProviderType.SPOTIFY, "user-1")}
        )

    app.dependency_overrides[get_playlist_management_service] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    reset_mock_libraries()


def first_two_playlists(client: TestClient) -> list[dict]:
    return client.get(BASE).json()["playlists"][:2]


class TestProvidersEndpoints:
    """Integration tests for /v1/providers."""

    def test_requires_authentication(self, app):
        # The Google client normally comes from the app lifespan
        app.dependency_overrides[_get_google_client] = lambda: AsyncMock()

        response = TestClient(app).get(BASE)

        app.dependency_overrides.clear()
        assert response.status_code == 401

    def test_list_providers(self, client):
        response = client.get("/v1/providers")

        assert response.status_code == 200
        assert response.json()["providers"] == [
            {"id": "spotify", "name": "Spotify", "is_mock": True}
        ]

    def test_unknown_provider_is_rejected(self, client):
        assert client.get("/v1/providers/napster/playlists").status_code == 422

    def test_provider_not_configured_returns_404(self, client):
        assert client.get("/v1/providers/apple_music/playlists").status_code == 404

    def test_get_tracks_and_remove(self, client):
        playlist = first_two_playlists(client)[0]
        tracks = client.get(f"{BASE}/{playlist['id']}/tracks").json()["tracks"]

        response = client.post(
            f"{BASE}/{playlist['id']}/tracks/remove",
            json={"item_ids": [tracks[0]["item_id"], tracks[1]["item_id"]]},
        )

        assert response.status_code == 200
        assert response.json() == {"removed_count": 2, "requested_count": 2}
        remaining = client.get(f"{BASE}/{playlist['id']}/tracks").json()["tracks"]
        assert len(remaining) == len(tracks) - 2

    def test_unknown_playlist_returns_404(self, client):
        assert client.get(f"{BASE}/nope/tracks").status_code == 404

    def test_merge_requires_exactly_one_destination(self, client):
        a, b = first_two_playlists(client)

        response = client.post(
            f"{BASE}/merge",
            json={
                "source_playlist_ids": [a["id"]],
                "target_playlist_id": b["id"],
                "new_playlist_name": "Both",
            },
        )

        assert response.status_code == 422

    def test_merge_into_new_playlist(self, client):
        a, b = first_two_playlists(client)

        response = client.post(
            f"{BASE}/merge",
            json={"source_playlist_ids": [a["id"], b["id"]], "new_playlist_name": "Both"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["playlist"]["name"] == "Both"
        assert body["added_count"] == body["playlist"]["track_count"] > 0

    def test_create_from_difference(self, client):
        a, b = first_two_playlists(client)

        response = client.post(
            BASE,
            json={
                "name": "Only in A",
                "source_playlist_ids": [a["id"], b["id"]],
                "mode": "difference",
            },
        )

        assert response.status_code == 201
        assert response.json()["playlist"]["name"] == "Only in A"
