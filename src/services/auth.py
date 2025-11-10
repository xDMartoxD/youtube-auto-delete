import jwt
import time
import uuid
import logging
from datetime import datetime, timezone
from src.core.config import config
from src.core.exceptions import (
    AuthenticationFailedError,
    LogoutFailedError,
    YoutubeAutoDeleteApiError,
)
from src.db.models.auth import TokenModel
from src.db.repositories.auth import AuthRepository
from src.services.google_client import GoogleClient
from src.schemas.auth import (
    GoogleUserResponse,
    SessionCookieData,
    SessionPayload,
    SessionValidation,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        client: GoogleClient,
        auth_repo: AuthRepository,
    ):
        self.client = client
        self.auth_repo = auth_repo

    async def exchange_code(
        self, code: str, redirect_uri: str
    ) -> tuple[GoogleUserResponse, str, int]:
        """
        Exchange code and persist user data.
        Returns user data, session token, and refresh_expires_at.
        """
        try:
            auth_response = await self.client.exchange_code(code, redirect_uri)
            user_response = await self.client.decode_id_token(auth_response.id_token)

            token_model = TokenModel.from_dto(auth_response, user_response)

            # Usar transacciones para operaciones críticas
            await self.auth_repo.insert(token_model)

            # Generar token de sesión
            session_token = self._generate_session_token(
                user_response.sub,
                token_model.refresh_expires_at,
            )

            # Retornar datos del usuario, token de sesión y refresh_expires_at
            return user_response, session_token, token_model.refresh_expires_at

        except Exception as e:
            logger.exception("exchange_code failed")
            raise YoutubeAutoDeleteApiError() from e

    def _generate_session_token(self, sub: str, exp: int) -> str:
        """Genera un token JWT para la sesión."""
        payload: SessionPayload = {
            "sub": sub,
            "iat": int(time.time()),
            "exp": exp,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(dict(payload), config.jwt_secret, algorithm="HS256")

    def get_session_cookie_data(
        self, session_token: str, expires_at: int
    ) -> SessionCookieData:
        """Retorna los datos necesarios para crear la cookie de sesión."""
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

        # Obtener información del usuario desde Google
        user_info_data = await self.client.get_user_info(access_token)

        # Convertir GoogleUserInfo a GoogleUserResponse
        # Usar valores por defecto para los campos JWT
        return GoogleUserResponse.from_user_info(
            user_info=user_info_data,
            iss="https://accounts.google.com",
            aud=str(config.google_client_id),
            iat=int(time.time()),
            exp=int(time.time()) + 3600,  # 1 hora
        )

    async def validate_and_refresh_session(
        self, session_token: str
    ) -> SessionValidation:
        """Valida el token de sesión y refresca el access token si es necesario."""
        try:
            # Decodificar y validar el token de sesión
            payload = self._decode_session_token(session_token)
            user_sub, session_id = payload["sub"], payload["jti"]

            # Obtener datos del token desde la base de datos
            token_data = await self._get_token_data(user_sub)

            # Verificar si necesita refresh y procesar
            if self._needs_token_refresh(token_data):
                return await self._refresh_token_and_return(
                    user_sub, session_id, token_data
                )
            else:
                return self._return_current_token(user_sub, session_id, token_data)

        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            raise AuthenticationFailedError(message="Session expired")
        except jwt.InvalidTokenError:
            logger.warning("Invalid session token")
            raise AuthenticationFailedError(message="Invalid session token")
        except Exception as e:
            logger.error(f"Error in session validation: {str(e)}")
            raise AuthenticationFailedError(message="Authentication error")

    def _decode_session_token(self, session_token: str) -> SessionPayload:
        """Decodifica y valida el token de sesión."""
        payload: SessionPayload = jwt.decode(
            session_token, config.jwt_secret, algorithms=["HS256"]
        )

        # Verificar expiración del token de sesión
        exp = payload.get("exp")
        if exp and datetime.now(tz=timezone.utc).timestamp() > exp:
            raise AuthenticationFailedError(message="Session expired")

        return payload

    async def _get_token_data(self, user_sub: str) -> TokenModel:
        """Obtiene los datos del token desde la base de datos."""
        token_data = await self.auth_repo.get_token_by_sub(user_sub)
        if not token_data:
            logger.warning(f"No token data found for user: {user_sub}")
            raise AuthenticationFailedError(message="Token data not found")
        return token_data

    def _needs_token_refresh(self, token_data: TokenModel) -> bool:
        """Verifica si el access token necesita ser refrescado."""
        current_time = datetime.now(timezone.utc).timestamp()
        return bool(token_data.expires_at and current_time >= token_data.expires_at)

    async def _refresh_token_and_return(
        self, user_sub: str, session_id: str, token_data: TokenModel
    ) -> SessionValidation:
        """Refresca el token y retorna los datos actualizados."""
        current_time = datetime.now(timezone.utc).timestamp()

        # Verificar si el refresh token también está expirado
        if (
            token_data.refresh_expires_at
            and current_time >= token_data.refresh_expires_at
        ):
            logger.error(f"Both access and refresh tokens expired for user: {user_sub}")
            raise AuthenticationFailedError(
                message="Both access and refresh tokens expired"
            )

        try:
            logger.info(f"Access token expired for user: {user_sub}, refreshing...")

            # Refrescar el access token
            refresh_response = await self.client.refresh_access_token(
                token_data.refresh_token
            )

            # Actualizar datos en la base de datos
            await self._update_token_in_db(user_sub, refresh_response)

            # Generar nuevo token de sesión
            new_session_token = self._generate_refreshed_session_token(
                user_sub, session_id, refresh_response.expires_in
            )

            logger.info(f"Successfully refreshed access token for user: {user_sub}")

            return {
                "authenticated": True,
                "user_sub": user_sub,
                "session_id": session_id,
                "access_token": refresh_response.access_token,
                "token_refreshed": True,
                "new_session_token": new_session_token,
                "refresh_expires_at": int(time.time())
                + refresh_response.refresh_token_expires_in,
            }

        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_sub}: {str(e)}")
            raise AuthenticationFailedError(message="Failed to refresh access token")

    async def _update_token_in_db(self, user_sub: str, refresh_response) -> None:
        """Actualiza los datos del token en la base de datos."""
        update_data = {
            "access_token": refresh_response.access_token,
            "expires_at": int(time.time()) + refresh_response.expires_in,
            "issued_at": int(time.time()),
        }
        await self.auth_repo.update_token(user_sub, update_data)

    def _generate_refreshed_session_token(
        self, user_sub: str, session_id: str, expires_in: int
    ) -> str:
        """Genera un nuevo token de sesión después del refresh."""
        payload: SessionPayload = {
            "sub": user_sub,
            "jti": session_id,
            "iat": int(time.time()),
            "exp": expires_in,
        }
        return jwt.encode(dict(payload), config.jwt_secret, algorithm="HS256")

    def _return_current_token(
        self, user_sub: str, session_id: str, token_data: TokenModel
    ) -> SessionValidation:
        """Retorna los datos del token actual sin refresh."""
        return {
            "authenticated": True,
            "user_sub": user_sub,
            "session_id": session_id,
            "access_token": token_data.access_token,
            "token_refreshed": False,
            "new_session_token": None,
            "refresh_expires_at": token_data.refresh_expires_at,
        }

    async def logout(self, session: SessionValidation) -> None:
        """Cierra la sesión del usuario."""
        try:
            await self.auth_repo.delete_token(session["user_sub"])
            await self.client.revoke_access_token(session["access_token"])
        except Exception as e:
            logger.error(f"Failed to logout user: {session['user_sub']}: {str(e)}")
            raise LogoutFailedError()
