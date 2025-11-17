"""Application service for authentication - orchestrates domain and infrastructure."""

import time
import logging
from datetime import datetime, timezone

import httpx
from pydantic import ValidationError
from googleapiclient.errors import HttpError

from src.core.config import config
from src.infrastructure.services.cache_service import CacheService
from src.core.exceptions import (
    AuthenticationFailedError,
    LogoutFailedError,
    YoutubeAutoDeleteApiError,
)
from src.schemas.auth import (
    GoogleUserResponse,
    SessionCookieData,
    SessionValidation,
)
from src.domain.aggregates.user_aggregate import UserAggregate
from src.domain.entities.session import Session
from src.domain.services.session_service import SessionService
from src.domain.repositories.user_repository import IUserRepository
from src.domain.events.user_authenticated import UserAuthenticated
from src.domain.events.session_refreshed import SessionRefreshed
from src.infrastructure.external_services.google_client import GoogleClient
from src.infrastructure.services.jwt_service import JWTService
from src.infrastructure.mappers.user_mapper import UserMapper
from src.infrastructure.persistence.models.token_model import TokenModel

logger = logging.getLogger(__name__)


class AuthService:
    """
    Application service - orchestrates domain and infrastructure.
    NO contiene lógica de negocio, solo coordina operaciones.
    """

    def __init__(
        self,
        client: GoogleClient,
        user_repo: IUserRepository,
        session_service: SessionService | None = None,
        jwt_service: JWTService | None = None,
        cache_service: CacheService | None = None,
    ):
        self.client = client
        self.user_repo = user_repo
        self.session_service = session_service or SessionService()
        self.jwt_service = jwt_service or JWTService()
        self.cache_service = cache_service or CacheService()

    async def exchange_code(
        self, code: str, redirect_uri: str
    ) -> tuple[GoogleUserResponse, str, int]:
        """
        Exchange code and persist user data.
        Returns user data, session token, and refresh_expires_at.
        """
        try:
            # INFRASTRUCTURE: Exchange code with Google
            auth_response = await self.client.exchange_code(code, redirect_uri)
            user_response = await self.client.decode_id_token(auth_response.id_token)

            # INFRASTRUCTURE: Create TokenModel for persistence
            token_model = TokenModel.from_dto(auth_response, user_response)

            # DOMAIN: Create UserAggregate
            user = UserAggregate.create(
                user_id=user_response.sub,
                email=user_response.email,
                name=user_response.name,
                picture=user_response.picture,
            )

            # DOMAIN: Create session in aggregate
            session = user.create_session(
                access_token=token_model.access_token,
                refresh_token=token_model.refresh_token,
                expires_at=token_model.expires_at,
                refresh_expires_at=token_model.refresh_expires_at,
            )

            # INFRASTRUCTURE: Save to database
            # Insert TokenModel using the user repository
            await self.user_repo.insert_token_model(token_model)

            # INFRASTRUCTURE: Generate session token
            session_token = self.jwt_service.encode(
                user_id=user.user_id,
                expires_at=token_model.refresh_expires_at,
            )

            # DOMAIN: Raise domain event
            # (In a full implementation, we'd use an event bus)
            event = UserAuthenticated(
                user_id=user.user_id,
                email=user.email.value,
                session_id=session.session_id or "",
            )
            logger.info(f"Domain event: {event}")

            return user_response, session_token, token_model.refresh_expires_at

        except (AuthenticationFailedError, ValueError) as e:
            logger.error(f"exchange_code failed: {e}")
            raise
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"HTTP error in exchange_code: {e}")
            raise AuthenticationFailedError(message="Failed to communicate with Google API") from e
        except ValidationError as e:
            logger.error(f"Validation error in exchange_code: {e}")
            raise AuthenticationFailedError(message="Invalid response from Google API") from e
        except Exception as e:
            logger.exception("Unexpected error in exchange_code")
            raise YoutubeAutoDeleteApiError() from e

    def get_session_cookie_data(
        self, session_token: str, expires_at: int
    ) -> SessionCookieData:
        """Returns the data needed to create the session cookie."""
        current_time = int(time.time())
        max_age = max(0, expires_at - current_time)

        return SessionCookieData(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=max_age,
            path="/",
        )

    async def get_user_profile(self, access_token: str) -> GoogleUserResponse:
        """Get user profile from Google."""
        async def _fetch_profile() -> GoogleUserResponse:
            """Fetch user profile from Google."""
            # INFRASTRUCTURE: Get user info from Google
            user_info_data = await self.client.get_user_info(access_token)

            # Convert GoogleUserInfo to GoogleUserResponse
            return GoogleUserResponse.from_user_info(
                user_info=user_info_data,
                iss="https://accounts.google.com",
                aud=str(config.google_client_id) if config.google_client_id else "google",
                iat=int(time.time()),
                exp=int(time.time()) + 3600,  # 1 hour
            )

        # INFRASTRUCTURE: Get from cache or fetch
        cached_result = await self.cache_service.get("user_profile", access_token)
        
        if cached_result:
            return GoogleUserResponse(**cached_result)

        # Cache miss - fetch and cache
        result = await _fetch_profile()
        await self.cache_service.set(
            "user_profile",
            result.model_dump(),
            expire=config.cache_ttl_user_profile,
            access_token=access_token,
        )
        
        return result

    async def validate_and_refresh_session(
        self, session_token: str
    ) -> SessionValidation:
        """Validates the session token and refreshes the access token if necessary."""
        try:
            # INFRASTRUCTURE: Decode JWT
            payload = self.jwt_service.decode(session_token)
            user_sub, session_id = payload["sub"], payload["jti"]

            # INFRASTRUCTURE: Get user aggregate from repository
            user = await self.user_repo.find_by_id(user_sub)
            if not user:
                raise AuthenticationFailedError(message="User not found")

            # INFRASTRUCTURE: Get token data for updates (if repository supports it)
            token_data = None
            if hasattr(self.user_repo, "get_token_by_sub"):
                token_data = await self.user_repo.get_token_by_sub(user_sub)  # type: ignore

            if not user.session:
                raise AuthenticationFailedError(message="No active session")

            # DOMAIN: Use domain service to check if refresh is needed
            if self.session_service.should_refresh_token(user.session):
                return await self._refresh_token_and_return(user, token_data)
            else:
                return self._return_current_token(user.session, user_sub, session_id)

        except AuthenticationFailedError:
            raise
        except ValueError as e:
            logger.error(f"Value error in session validation: {e}")
            raise AuthenticationFailedError(message="Invalid session token") from e
        except KeyError as e:
            logger.error(f"Missing key in session validation: {e}")
            raise AuthenticationFailedError(message="Invalid session token format") from e
        except Exception as e:
            logger.error(f"Unexpected error in session validation: {e}")
            raise AuthenticationFailedError(message="Authentication error") from e

    async def _refresh_token_and_return(
        self, user: UserAggregate, token_data: TokenModel | None
    ) -> SessionValidation:
        """Refreshes the token and returns updated data."""
        if not user.session:
            raise AuthenticationFailedError(message="No active session")

        current_time = datetime.now(timezone.utc)

        # DOMAIN: Check if session is fully expired
        if self.session_service.is_session_expired(user.session, current_time):
            logger.error(
                f"Both access and refresh tokens expired for user: {user.user_id}"
            )
            raise AuthenticationFailedError(
                message="Both access and refresh tokens expired"
            )

        try:
            logger.info(f"Access token expired for user: {user.user_id}, refreshing...")

            # INFRASTRUCTURE: Refresh token with Google
            refresh_response = await self.client.refresh_access_token(
                user.session.refresh_token
            )

            # DOMAIN: Update session in aggregate
            new_expires_at = int(time.time()) + refresh_response.expires_in
            user.refresh_session(refresh_response.access_token, new_expires_at)

            # INFRASTRUCTURE: Update in database
            if token_data and hasattr(self.user_repo, "update_token"):
                update_data = {
                    "access_token": refresh_response.access_token,
                    "expires_at": new_expires_at,
                    "issued_at": int(time.time()),
                }
                await self.user_repo.update_token(user.user_id, update_data)  # type: ignore

            # INFRASTRUCTURE: Generate new session token
            new_refresh_expires_at = (
                int(time.time()) + refresh_response.refresh_token_expires_in
            )
            new_session_token = self.jwt_service.encode(
                user_id=user.user_id,
                expires_at=new_refresh_expires_at,
                session_id=user.session.session_id,
            )

            logger.info(f"Successfully refreshed access token for user: {user.user_id}")

            # DOMAIN: Raise domain event
            event = SessionRefreshed(
                user_id=user.user_id,
                session_id=user.session.session_id or "",
            )
            logger.info(f"Domain event: {event}")

            return {
                "authenticated": True,
                "user_sub": user.user_id,
                "session_id": user.session.session_id or "",
                "access_token": refresh_response.access_token,
                "token_refreshed": True,
                "new_session_token": new_session_token,
                "refresh_expires_at": new_refresh_expires_at,
            }

        except AuthenticationFailedError:
            raise
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"HTTP error refreshing token for user {user.user_id}: {e}")
            raise AuthenticationFailedError(message="Failed to communicate with Google API") from e
        except ValidationError as e:
            logger.error(f"Validation error refreshing token for user {user.user_id}: {e}")
            raise AuthenticationFailedError(message="Invalid response from Google API") from e
        except Exception as e:
            logger.error(f"Unexpected error refreshing token for user {user.user_id}: {e}")
            raise AuthenticationFailedError(message="Failed to refresh access token") from e

    def _return_current_token(
        self, session: Session, user_sub: str, session_id: str
    ) -> SessionValidation:
        """Returns current token data without refresh."""
        return {
            "authenticated": True,
            "user_sub": user_sub,
            "session_id": session_id,
            "access_token": session.access_token,
            "token_refreshed": False,
            "new_session_token": None,
            "refresh_expires_at": session.refresh_expires_at,
        }

    async def logout(self, session: SessionValidation) -> None:
        """Closes the user's session."""
        try:
            # INFRASTRUCTURE: Delete token from database
            if hasattr(self.user_repo, "delete_token"):
                await self.user_repo.delete_token(session["user_sub"])  # type: ignore
            else:
                await self.user_repo.delete(session["user_sub"])

            # INFRASTRUCTURE: Revoke token with Google
            await self.client.revoke_access_token(session["access_token"])
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(f"HTTP error revoking token for user {session['user_sub']}: {e}")
            # Continue with logout even if revoke fails
        except Exception as e:
            logger.error(f"Failed to logout user {session['user_sub']}: {e}")
            raise LogoutFailedError() from e
