from functools import lru_cache
from typing import Annotated, AsyncGenerator, Generator
import logging
from fastapi import Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.exceptions import AuthenticationFailedError
from src.schemas.auth import SessionValidation
from src.application.services.youtube_service import YoutubeService
from src.application.services.auth_service import AuthService
from src.application.services.suggestions_service import SuggestionsService
from src.infrastructure.external_services.google_client import GoogleClient
from src.infrastructure.repositories.dynamodb_user_repository import (
    DynamoDBUserRepository,
)
from src.infrastructure.repositories.dynamodb_suggestion_repository import (
    DynamoDBSuggestionRepository,
)
from src.domain.services.session_service import SessionService
from src.domain.services.video_filter_service import VideoFilterService
from src.domain.services.suggestion_service import SuggestionService
from src.infrastructure.services.jwt_service import JWTService
from src.infrastructure.services.cache_service import CacheService

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
        session_token = request.cookies.get("session_token")
        # Return a placeholder for documentation if token is missing
        # The actual validation happens in get_current_session
        if not session_token:
            session_token = ""
        return HTTPAuthorizationCredentials(scheme="Cookie", credentials=session_token)


# Security scheme for documentation
cookie_security = CookieSecurity()


@lru_cache
def _get_user_repository() -> DynamoDBUserRepository:
    return DynamoDBUserRepository()


def _get_google_client(request: Request) -> GoogleClient:
    # Returns the unique instance created in lifespan (request.app.state)
    return request.app.state.google_client


def get_auth_service(
    user_repo: DynamoDBUserRepository = Depends(_get_user_repository),
    google_client: GoogleClient = Depends(_get_google_client),
) -> Generator[AuthService, None, None]:
    """Dependency to create AuthService with domain and infrastructure injection."""
    # Create instances of domain and infrastructure services
    session_service = SessionService()
    jwt_service = JWTService()

    svc = AuthService(
        client=google_client,
        user_repo=user_repo,
        session_service=session_service,
        jwt_service=jwt_service,
    )
    try:
        yield svc
    finally:
        pass


auth_service_dependency = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_session(
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    session_cookie: HTTPAuthorizationCredentials = Depends(cookie_security),
) -> AsyncGenerator[SessionValidation, None]:
    credentials = session_cookie.credentials
    # Validate that we have a non-empty token before attempting to decode
    if not credentials or credentials.strip() == "":
        raise AuthenticationFailedError(message="Session token not found in cookie")
    
    # Basic JWT format validation (should have 3 segments separated by dots)
    if credentials.count(".") != 2:
        logger.warning(f"Invalid JWT format: token has {credentials.count('.')} segments instead of 2")
        raise AuthenticationFailedError(message="Invalid session token format")

    session = await auth_service.validate_and_refresh_session(credentials)

    try:
        yield session
    finally:
        # Update cookie ONLY after endpoint completes successfully
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
    video_filter_service = VideoFilterService()
    cache_service = CacheService()
    service = YoutubeService(
        session,
        video_filter_service=video_filter_service,
        cache_service=cache_service,
    )
    await service.initialize()
    try:
        yield service
    finally:
        pass


youtube_service_dependency = Annotated[YoutubeService, Depends(get_youtube_service)]


@lru_cache
def _get_suggestions_repository() -> DynamoDBSuggestionRepository:
    return DynamoDBSuggestionRepository()


def get_suggestions_service(
    suggestions_repo: DynamoDBSuggestionRepository = Depends(
        _get_suggestions_repository
    ),
) -> Generator[SuggestionsService, None, None]:
    """Dependency to create SuggestionsService with domain injection."""
    suggestion_service = SuggestionService()

    svc = SuggestionsService(
        suggestion_repo=suggestions_repo,
        suggestion_service=suggestion_service,
    )
    try:
        yield svc
    finally:
        pass


suggestions_service_dependency = Annotated[
    SuggestionsService, Depends(get_suggestions_service)
]
