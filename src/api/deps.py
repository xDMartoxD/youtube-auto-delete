# ...existing code...
from functools import lru_cache
from typing import Generator
from fastapi import Depends, HTTPException, Request


from src.domain.services.youtube import YoutubeService
from src.domain.services.auth import AuthService
from src.domain.services.google_client import GoogleClient
from src.db.repositories.auth import AuthRepository
from src.middlewares.session import get_request_state, RequestState


@lru_cache
def get_auth_repository() -> AuthRepository:
    return AuthRepository()


def get_google_client(request: Request) -> GoogleClient:
    # Devuelve la instancia única creada en lifespan (request.app.state)
    return request.app.state.google_client


def get_auth_service(
    auth_repo: AuthRepository = Depends(get_auth_repository),
    google_client: GoogleClient = Depends(get_google_client),
) -> Generator[AuthService, None, None]:
    svc = AuthService(google_client, auth_repo)
    try:
        yield svc
    finally:
        # cleanup si es necesario
        pass


def get_request_state_dependency(request: Request) -> RequestState:
    """Dependency para obtener el estado del request con tipado correcto."""
    return get_request_state(request)


async def get_youtube_service_for_user(
    request: Request,
    google_client: GoogleClient = Depends(get_google_client),
    auth_repo: AuthRepository = Depends(get_auth_repository),
    request_state: RequestState = Depends(get_request_state_dependency),
) -> YoutubeService:
    """Create and initialize YouTube service for authenticated user."""
    if not request_state["user_sub"]:
        raise HTTPException(status_code=401, detail="Authentication required")

    service = YoutubeService(
        google_client,
        auth_repo,
        request_state["user_sub"],
        request_state["access_token"],
    )
    await service.initialize()  # Inicializar en el dependency
    return service
