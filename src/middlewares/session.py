# src/middlewares/session.py
import logging
import jwt
import time
from datetime import datetime, timezone
from typing import TypedDict, Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from src.core.config import config
from src.core.exceptions import AuthenticationFailedError
from src.domain.schemas.auth import SessionPayload
from src.domain.services.auth import AuthService
from src.domain.services.google_client import GoogleClient
from src.db.repositories.auth import AuthRepository
from src.db.models.auth import TokenModel

logger = logging.getLogger(__name__)


class RequestState(TypedDict):
    """Estado del request después de la autenticación."""

    user_sub: str | None = None
    session_id: str | None = None
    access_token: str | None = None
    token_data: TokenModel | None = None
    token_refreshed: bool
    new_session_token: str | None = None


def _get_auth_service() -> AuthService:
    """Crea una instancia de AuthService para el middleware."""
    google_client = GoogleClient()
    auth_repo = AuthRepository()
    return AuthService(google_client, auth_repo)


def get_request_state(request: Request) -> RequestState:
    """Obtiene el estado del request con tipado correcto."""
    return RequestState(
        user_sub=getattr(request.state, "user_sub", None),
        session_id=getattr(request.state, "session_id", None),
        access_token=getattr(request.state, "access_token", None),
        token_data=getattr(request.state, "token_data", None),
        token_refreshed=getattr(request.state, "token_refreshed", False),
        new_session_token=getattr(request.state, "new_session_token", None),
    )


class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, protected_paths: list[str] = []):
        super().__init__(app)
        self.protected_paths = protected_paths

    async def dispatch(self, request: Request, call_next):
        # Verificar si la ruta requiere autenticación
        if not self._requires_auth(request.url.path):
            request.state.user_sub = None
            request.state.access_token = None
            request.state.token_data = None
            return await call_next(request)

        # Obtener el token de sesión de la cookie
        session_token = request.cookies.get("session_token")

        if not session_token:
            return JSONResponse(
                content={"detail": "Session token not found"},
                status_code=401,
            )

        # Usar AuthService para validar y refrescar si es necesario
        auth_service = _get_auth_service()
        auth_result = await auth_service.validate_and_refresh_session(session_token)

        # Agregar datos del usuario al request
        request.state.user_sub = auth_result["user_sub"]
        request.state.session_id = auth_result["session_id"]
        request.state.access_token = auth_result["access_token"]
        request.state.token_refreshed = auth_result.get("token_refreshed", False)
        request.state.new_session_token = auth_result.get("new_session_token")

        # Continuar con la request
        response = await call_next(request)

        # Si el token fue refrescado, actualizar la cookie
        if auth_result.get("token_refreshed", False) and auth_result.get(
            "new_session_token"
        ):
            self._update_session_cookie(
                response,
                auth_result["new_session_token"],
                auth_result["refresh_expires_at"],
            )

        return response

    def _requires_auth(self, path: str) -> bool:
        """Verifica si la ruta requiere autenticación."""
        return any(
            path.startswith(protected_path) for protected_path in self.protected_paths
        )

    def _update_session_cookie(
        self, response, session_token: str, refresh_expires_at: int
    ) -> None:
        """Actualiza la cookie de sesión con el nuevo token."""
        current_time = int(time.time())
        max_age = max(0, refresh_expires_at - current_time)

        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=max_age,
            path="/",
        )

        logger.info("Session cookie updated after token refresh")
