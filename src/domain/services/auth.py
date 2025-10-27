import jwt
import time
import uuid
import logging
from datetime import datetime, timezone
from src.core.config import config
from src.core.exceptions import AuthenticationFailedError, YoutubeAutoDeleteApiError
from src.db.models.auth import TokenModel
from src.db.repositories.auth import AuthRepository
from src.domain.services.google_client import GoogleClient
from src.domain.schemas.auth import (
    GoogleUserResponse,
    SessionCookieData,
    SessionPayload,
    SessionValidationSuccess,
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
                token_model.expires_at,
                token_model.refresh_expires_at,
            )

            # Retornar datos del usuario, token de sesión y refresh_expires_at
            return user_response, session_token, token_model.refresh_expires_at

        except Exception as e:
            logger.exception("exchange_code failed")
            raise YoutubeAutoDeleteApiError() from e

    def _generate_session_token(self, sub: str, refresh_at: int, exp: int) -> str:
        """Genera un token JWT para la sesión."""
        payload: SessionPayload = {
            "sub": sub,
            "iat": int(time.time()),
            "refresh_at": refresh_at,
            "exp": exp,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, config.jwt_secret, algorithm="HS256")

    def get_session_cookie_data(
        self, session_token: str, refresh_expires_at: int
    ) -> SessionCookieData:
        """Retorna los datos necesarios para crear la cookie de sesión."""
        current_time = int(time.time())
        max_age = max(0, refresh_expires_at - current_time)

        return SessionCookieData(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=max_age,
            path="/",
        )

    async def get_user_profile(self, sub: str) -> GoogleUserResponse:
        token_data = await self.auth_repo.get_token_by_sub(sub)
        if not token_data:
            raise AuthenticationFailedError(message="Token not found")

        # Obtener información del usuario desde Google
        user_info_data = await self.client.get_user_info(token_data.access_token)

        # Convertir GoogleUserInfo a GoogleUserResponse
        # Usar valores por defecto para los campos JWT
        return GoogleUserResponse.from_user_info(
            user_info=user_info_data,
            iss="https://accounts.google.com",
            aud=config.google_client_id,
            iat=int(time.time()),
            exp=int(time.time()) + 3600,  # 1 hora
        )

    async def validate_and_refresh_session(
        self, session_token: str
    ) -> SessionValidationSuccess:
        """
        Valida el token de sesión y refresca el access token si es necesario.
        Retorna información completa para el middleware.
        """
        try:
            # Decodificar el token de sesión
            payload: SessionPayload = jwt.decode(
                session_token, config.jwt_secret, algorithms=["HS256"]
            )

            # Verificar expiración del token de sesión
            exp = payload.get("exp")
            if exp and datetime.now(tz=timezone.utc).timestamp() > exp:
                raise AuthenticationFailedError(message="Session expired")

            user_sub = payload.get("sub")
            session_id = payload.get("jti")

            # Obtener datos del token desde la base de datos
            token_data = await self.auth_repo.get_token_by_sub(user_sub)

            if not token_data:
                logger.warning(f"No token data found for user: {user_sub}")
                raise AuthenticationFailedError(message="Token data not found")

            # Verificar si el access token está expirado y necesita refresh
            current_time = datetime.now(timezone.utc).timestamp()
            token_refreshed = False
            new_session_token = None
            refresh_expires_at = token_data.refresh_expires_at

            if token_data.expires_at and current_time >= token_data.expires_at:
                logger.info(f"Access token expired for user: {user_sub}, refreshing...")

                # Verificar si el refresh token también está expirado
                if (
                    token_data.refresh_expires_at
                    and current_time >= token_data.refresh_expires_at
                ):
                    logger.error(
                        f"Both access and refresh tokens expired for user: {user_sub}"
                    )
                    raise AuthenticationFailedError(
                        message="Both access and refresh tokens expired"
                    )
                try:
                    # Refrescar el access token usando el método del servicio
                    refresh_response = await self.client.refresh_access_token(
                        token_data.refresh_token
                    )

                    # Actualizar datos en la base de datos
                    update_data = {
                        "access_token": refresh_response.access_token,
                        "expires_at": int(time.time()) + refresh_response.expires_in,
                        "issued_at": int(time.time()),
                    }

                    await self.auth_repo.update_token(user_sub, update_data)

                    # Generar nuevo token de sesión con la misma información
                    new_session_token_payload: SessionPayload = {
                        "sub": user_sub,
                        "jti": session_id,
                        "iat": int(time.time()),
                        "exp": refresh_response.expires_in,
                        "refresh_at": refresh_response.refresh_token_expires_in,
                    }
                    new_session_token = jwt.encode(
                        new_session_token_payload,
                        config.jwt_secret,
                        algorithm="HS256",
                    )

                    token_refreshed = True
                    logger.info(
                        f"Successfully refreshed access token for user: {user_sub}"
                    )
                    return {
                        "authenticated": True,
                        "user_sub": user_sub,
                        "session_id": session_id,
                        "access_token": refresh_response.access_token,
                        "token_refreshed": token_refreshed,
                        "new_session_token": new_session_token,
                        "refresh_expires_at": refresh_expires_at,
                    }

                except Exception as e:
                    logger.error(
                        f"Failed to refresh token for user {user_sub}: {str(e)}"
                    )
                    raise AuthenticationFailedError(
                        message="Failed to refresh access token"
                    )

            # Si el token no necesita refresh, retornar datos actuales
            return {
                "authenticated": True,
                "user_sub": user_sub,
                "session_id": session_id,
                "access_token": token_data.access_token,
                "token_refreshed": token_refreshed,
                "new_session_token": None,
                "refresh_expires_at": refresh_expires_at,
            }

        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            raise AuthenticationFailedError(message="Session expired")
        except jwt.InvalidTokenError:
            logger.warning("Invalid session token")
            raise AuthenticationFailedError(message="Invalid session token")
        except Exception as e:
            logger.error(f"Error in session validation: {str(e)}")
            raise AuthenticationFailedError(message="Authentication error")
