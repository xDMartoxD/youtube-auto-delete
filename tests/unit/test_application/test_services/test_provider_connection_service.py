"""
Unit tests for ProviderConnectionService (OAuth connect flow).
"""

import time
from urllib.parse import parse_qs, urlparse

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.services.provider_connection_service import (
    ProviderConnectionService,
)
from src.core.config import config
from src.core.exceptions import (
    InvalidPlaylistOperationError,
    ProviderNotSupportedError,
    ProviderRequestError,
)
from src.domain.providers import ProviderType
from src.infrastructure.external_services.spotify_client import (
    SpotifyApiError,
    SpotifyClient,
    TokenGrant,
)


@pytest.fixture
def spotify_configured(monkeypatch):
    monkeypatch.setattr(config, "spotify_client_id", "client-id")
    monkeypatch.setattr(config, "spotify_client_secret", "client-secret")


@pytest.fixture
def client():
    real = SpotifyClient()
    fake = MagicMock(wraps=real)
    fake.authorize_url.side_effect = real.authorize_url
    fake.exchange_code = AsyncMock(
        return_value=TokenGrant("access", int(time.time()) + 3600, "refresh", "scope")
    )
    return fake


@pytest.fixture
def connections():
    return AsyncMock()


@pytest.fixture
def service(client, connections):
    return ProviderConnectionService(client, connections)


def state_from(url: str) -> str:
    return parse_qs(urlparse(url).query)["state"][0]


class TestProviderConnectionService:
    def test_not_configured_is_rejected(self, service, monkeypatch):
        monkeypatch.setattr(config, "spotify_client_secret", None)

        with pytest.raises(ProviderNotSupportedError):
            service.authorize_url("u1", ProviderType.SPOTIFY)

    def test_only_connectable_providers(self, service, spotify_configured):
        with pytest.raises(ProviderNotSupportedError):
            service.authorize_url("u1", ProviderType.APPLE_MUSIC)

    def test_authorize_url_requests_playlist_scopes(self, service, spotify_configured):
        url = service.authorize_url("u1", ProviderType.SPOTIFY)

        query = parse_qs(urlparse(url).query)
        assert query["client_id"] == ["client-id"]
        assert "playlist-modify-private" in query["scope"][0]
        assert query["redirect_uri"] == [config.spotify_redirect_uri]

    @pytest.mark.asyncio
    async def test_complete_stores_tokens_for_the_user_in_state(
        self, service, connections, spotify_configured
    ):
        state = state_from(service.authorize_url("u1", ProviderType.SPOTIFY))

        await service.complete(ProviderType.SPOTIFY, "code", state)

        saved = connections.save.await_args.args[0]
        assert (saved.user_id, saved.access_token, saved.refresh_token) == (
            "u1",
            "access",
            "refresh",
        )

    @pytest.mark.asyncio
    async def test_tampered_state_is_rejected(self, service, connections, spotify_configured):
        state = state_from(service.authorize_url("u1", ProviderType.SPOTIFY))

        with pytest.raises(InvalidPlaylistOperationError):
            await service.complete(ProviderType.SPOTIFY, "code", state[:-2] + "xx")

        connections.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rejected_code_is_reported(self, service, client, spotify_configured):
        client.exchange_code.side_effect = SpotifyApiError(400, "invalid_grant")
        state = state_from(service.authorize_url("u1", ProviderType.SPOTIFY))

        with pytest.raises(ProviderRequestError):
            await service.complete(ProviderType.SPOTIFY, "code", state)

    @pytest.mark.asyncio
    async def test_find_returns_nothing_when_not_configured(
        self, service, connections, monkeypatch
    ):
        monkeypatch.setattr(config, "spotify_client_id", None)

        assert await service.find("u1", ProviderType.SPOTIFY) is None
        connections.find.assert_not_awaited()
