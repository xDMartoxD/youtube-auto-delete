"""Spotify Accounts + Web API client - infrastructure service."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from src.core.config import config

logger = logging.getLogger(__name__)

ACCOUNTS_URL = "https://accounts.spotify.com"
API_URL = "https://api.spotify.com/v1"
SCOPES = " ".join(
    [
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-read-private",
    ]
)
MAX_RATE_LIMIT_RETRIES = 3


@dataclass(frozen=True, slots=True)
class TokenGrant:
    access_token: str
    expires_at: int
    refresh_token: str | None
    scope: str


class SpotifyApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"Spotify API {status}: {message}")


class SpotifyClient:
    """Thin async wrapper; one instance per app (created in the lifespan)."""

    def __init__(self, timeout: float = 15.0):
        self._http = httpx.AsyncClient(timeout=timeout)

    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": config.spotify_client_id,
                "response_type": "code",
                "redirect_uri": config.spotify_redirect_uri,
                "scope": SCOPES,
                "state": state,
            }
        )
        return f"{ACCOUNTS_URL}/authorize?{query}"

    async def exchange_code(self, code: str) -> TokenGrant:
        return await self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.spotify_redirect_uri,
            }
        )

    async def refresh(self, refresh_token: str) -> TokenGrant:
        return await self._token_request(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )

    async def request(
        self,
        method: str,
        path: str,
        access_token: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the Web API. `path` may be relative ("/me") or a full `next` URL."""
        url = path if path.startswith("http") else f"{API_URL}{path}"
        headers = {"Authorization": f"Bearer {access_token}"}

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            resp = await self._http.request(
                method, url, headers=headers, params=params, json=json
            )
            if resp.status_code == 429 and attempt < MAX_RATE_LIMIT_RETRIES:
                wait = min(int(resp.headers.get("Retry-After", "1")), 10)
                logger.warning(f"Spotify rate limited, retrying in {wait}s")
                await asyncio.sleep(wait)
                continue
            break

        if resp.status_code >= 400:
            raise SpotifyApiError(resp.status_code, self._error_message(resp))
        return resp.json() if resp.content else {}

    async def _token_request(self, data: dict[str, str]) -> TokenGrant:
        resp = await self._http.post(
            f"{ACCOUNTS_URL}/api/token",
            data=data,
            auth=(config.spotify_client_id or "", config.spotify_client_secret or ""),
        )
        if resp.status_code >= 400:
            raise SpotifyApiError(resp.status_code, self._error_message(resp))
        body = resp.json()
        return TokenGrant(
            access_token=body["access_token"],
            expires_at=int(time.time()) + int(body.get("expires_in", 3600)),
            refresh_token=body.get("refresh_token"),
            scope=body.get("scope", ""),
        )

    @staticmethod
    def _error_message(resp: httpx.Response) -> str:
        try:
            body = resp.json()
        except ValueError:
            return resp.text[:200]
        error = body.get("error")
        if isinstance(error, dict):
            return str(error.get("message", error))
        return str(body.get("error_description") or error or body)

    async def close(self) -> None:
        await self._http.aclose()
