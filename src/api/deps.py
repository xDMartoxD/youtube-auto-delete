from functools import lru_cache
from typing import Annotated, AsyncGenerator, Generator
import logging
from fastapi import Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.exceptions import AuthenticationFailedError
from src.schemas.auth import SessionValidation
from src.services.youtube import YoutubeService
from src.services.auth import AuthService
from src.services.google_client import GoogleClient
from src.db.repositories.auth import AuthRepository

logger = logging.getLogger(__name__)


class CookieSecurity(HTTPBearer):
    """Security scheme that documents cookie-based authentication."""

    def __init__(self):
        super().__init__(
            scheme_name="Session Cookie",
            description="Session token from HTTP-only cookie",
            auto_error=False,
        )

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        """Extract session token from cookie for documentation purposes."""
        session_token = request.cookies.get("session_token", "session_token_required")
        return HTTPAuthorizationCredentials(scheme="Cookie", credentials=session_token)


# Security scheme para documentación
cookie_security = CookieSecurity()


@lru_cache
def _get_auth_repository() -> AuthRepository:
    return AuthRepository()


def _get_google_client(request: Request) -> GoogleClient:
    # Devuelve la instancia única creada en lifespan (request.app.state)
    return request.app.state.google_client


def get_auth_service(
    auth_repo: AuthRepository = Depends(_get_auth_repository),
    google_client: GoogleClient = Depends(_get_google_client),
) -> Generator[AuthService, None, None]:
    svc = AuthService(google_client, auth_repo)
    try:
        yield svc
    finally:
        # cleanup si es necesario
        pass


auth_service_dependency = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_session(
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    session_cookie: HTTPAuthorizationCredentials = Depends(cookie_security),
) -> AsyncGenerator[SessionValidation, None]:
    credentials = session_cookie.credentials
    if not credentials:
        raise AuthenticationFailedError(message="Session token not found in cookie")

    session = await auth_service.validate_and_refresh_session(credentials)

    try:
        yield session
    finally:
        # Actualizar cookie SOLO después de que el endpoint termine exitosamente
        if (
            session["token_refreshed"]
            and session["new_session_token"]
            and session["refresh_expires_at"]
        ):
            logger.info(f"Updating session cookie for user: {session['user_sub']}")
            response.set_cookie(
                **auth_service.get_session_cookie_data(
                    session["new_session_token"], session["refresh_expires_at"]
                ).model_dump()
            )


current_session_dependency = Annotated[SessionValidation, Depends(get_current_session)]


async def get_youtube_service(
    session: current_session_dependency,
) -> AsyncGenerator[YoutubeService, None]:
    """Create and initialize YouTube service for authenticated user."""
    yield YoutubeService(session)


youtube_service_dependency = Annotated[YoutubeService, Depends(get_youtube_service)]
