"""Google OAuth client - infrastructure service."""

import logging
from pydantic import ValidationError
from src.schemas.auth import (
    GoogleAuthResponse,
    GoogleUserResponse,
    GoogleUserInfo,
)
from src.core.config import config
from src.core.exceptions import AuthenticationFailedError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import RefreshError
import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleClient:
    """
    Async Google client for exchanging auth codes and decoding ID tokens.
    Infrastructure service - handles external API communication.
    """

    def __init__(self, timeout: float = 10.0):
        self._client = httpx.AsyncClient(timeout=timeout)

    async def exchange_code(self, code: str, redirect_uri: str) -> GoogleAuthResponse:
        """
        Exchange an authorization code for tokens (async).
        Raises ValueError on invalid response or missing configuration.
        """
        if not code:
            raise ValueError("empty code")

        # Validate configuration
        if not config.google_client_id:
            logger.error("Google client_id is not configured")
            raise AuthenticationFailedError(
                message="Google OAuth client_id is not configured"
            )
        if not config.google_client_secret:
            logger.error("Google client_secret is not configured")
            raise AuthenticationFailedError(
                message="Google OAuth client_secret is not configured"
            )

        # Log request details (without sensitive data)
        logger.info(
            f"Exchanging OAuth code with Google. redirect_uri={redirect_uri}, client_id={config.google_client_id[:20]}..."
        )

        try:
            resp = await self._client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": config.google_client_id,
                    "client_secret": config.google_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            body = resp.json()
            try:
                return GoogleAuthResponse.model_validate(body)
            except ValidationError as e:
                logger.error(f"Validation error parsing Google response: {e}")
                raise AuthenticationFailedError(
                    message="There was an error validating the response"
                )
        except httpx.HTTPStatusError as e:
            # Log the error response from Google for debugging
            error_detail = "Unknown error"
            try:
                error_body = e.response.json()
                error_detail = error_body.get(
                    "error_description", error_body.get("error", str(error_body))
                )
                logger.error(
                    f"Google OAuth error {e.response.status_code}: {error_detail}. redirect_uri={redirect_uri}, client_id={config.google_client_id[:20]}..."
                )
            except Exception:
                logger.error(
                    f"Google OAuth error {e.response.status_code}: {e.response.text}"
                )
            raise

    async def decode_id_token(self, token: str) -> GoogleUserResponse:
        """
        Verifies and decodes a Google ID token (async interface).
        Raises ValueError on invalid token or missing configuration.
        """
        if not token:
            raise ValueError("empty id token")

        client_id = config.google_client_id
        if not client_id:
            raise ValueError("GOOGLE_CLIENT_ID not configured")

        try:
            # verify_oauth2_token is synchronous but safe to call from async function
            # Add time tolerance to handle clock differences
            payload = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                client_id,
                clock_skew_in_seconds=60,  # 60 seconds tolerance
            )
            return GoogleUserResponse.model_validate(payload)
        except ValidationError as e:
            raise AuthenticationFailedError(
                message="There was an error validating the response"
            )

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """
        Get user information from Google using the official Google API library.
        """

        try:
            creds = Credentials(token=access_token)
            service = build("oauth2", "v2", credentials=creds)
            user_info = service.userinfo().get().execute()
            return GoogleUserInfo.model_validate(user_info)
        except (HttpError, RefreshError) as e:
            # RefreshError: Google rejected the access token (expired or revoked)
            raise AuthenticationFailedError(message="Google API error: " + str(e))
        except ValidationError as e:
            raise AuthenticationFailedError(
                message="There was an error validating the response"
            )

    async def refresh_access_token(self, refresh_token: str) -> GoogleAuthResponse:
        """
        Refresh an access token using the refresh token.
        """
        if not refresh_token:
            raise ValueError("empty refresh token")

        resp = await self._client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": config.google_client_id,
                "client_secret": config.google_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()
        try:
            return GoogleAuthResponse.model_validate(body)
        except ValidationError:
            raise AuthenticationFailedError(
                message="There was an error validating the refresh response"
            )

    async def revoke_access_token(self, access_token: str) -> None:
        """
        Revoke an access token using Google's OAuth2 revoke endpoint.
        """
        if not access_token:
            logger.warning("Attempted to revoke empty access token")
            return

        try:
            # Use Google's OAuth2 revoke endpoint directly
            resp = await self._client.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": access_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            # Google returns 200 even if token is already revoked or invalid
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Log but don't fail - token might already be revoked
            logger.warning(f"HTTP error revoking token: {e}")
        except Exception as e:
            logger.warning(f"Error revoking token: {e}")
            # Don't raise - logout should succeed even if revoke fails

    async def close(self):
        try:
            await self._client.aclose()
        except Exception:
            pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
