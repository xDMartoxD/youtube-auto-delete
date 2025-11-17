"""
Tests unitarios para AuthService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import time

from src.application.services.auth_service import AuthService
from src.schemas.auth import GoogleAuthResponse, GoogleUserResponse
from src.infrastructure.persistence.models.token_model import TokenModel
from src.domain.aggregates.user_aggregate import UserAggregate
from src.domain.services.session_service import SessionService
from src.infrastructure.services.jwt_service import JWTService
from src.infrastructure.services.cache_service import CacheService


class TestAuthService:
    """Tests para AuthService."""

    @pytest.fixture
    def auth_service(
        self, mock_google_client, mock_user_repository
    ):
        """Crear instancia de AuthService para testing."""
        session_service = SessionService()
        jwt_service = JWTService()
        cache_service = CacheService()
        
        return AuthService(
            client=mock_google_client,
            user_repo=mock_user_repository,
            session_service=session_service,
            jwt_service=jwt_service,
            cache_service=cache_service,
        )

    @pytest.mark.asyncio
    async def test_exchange_code_success(
        self, auth_service, sample_google_auth_response, sample_google_user_response
    ):
        """Test exitoso del intercambio de código."""
        # Arrange
        code = "test_code"
        redirect_uri = "http://localhost:3000/callback"

        # Mock Google responses
        auth_response = GoogleAuthResponse(**sample_google_auth_response)
        user_response = GoogleUserResponse(**sample_google_user_response)
        
        auth_service.client.exchange_code = AsyncMock(return_value=auth_response)
        auth_service.client.decode_id_token = AsyncMock(return_value=user_response)
        
        # Mock repository methods
        auth_service.user_repo.insert_token_model = AsyncMock()
        auth_service.user_repo.get_token_by_sub = AsyncMock(return_value=None)

        # Act
        user_data, session_token, refresh_expires_at = await auth_service.exchange_code(
            code, redirect_uri
        )

        # Assert
        auth_service.client.exchange_code.assert_called_once_with(code, redirect_uri)
        auth_service.client.decode_id_token.assert_called_once_with(auth_response.id_token)
        auth_service.user_repo.insert_token_model.assert_called_once()
        
        # Verificar que retorna los datos del usuario y token
        assert user_data is not None
        assert user_data.sub == sample_google_user_response["sub"]
        assert user_data.email == sample_google_user_response["email"]
        assert session_token is not None
        assert isinstance(session_token, str)
        assert refresh_expires_at > 0

    @pytest.mark.asyncio
    async def test_exchange_code_google_client_error(self, auth_service):
        """Test cuando el cliente de Google falla."""
        # Arrange
        code = "invalid_code"
        redirect_uri = "http://localhost:3000/callback"

        auth_service.client.exchange_code = AsyncMock(
            side_effect=Exception("Google API error")
        )

        # Act & Assert
        with pytest.raises(Exception):
            await auth_service.exchange_code(code, redirect_uri)

    def test_get_session_cookie_data(self, auth_service):
        """Test de obtención de datos de cookie de sesión."""
        # Arrange
        session_token = "test_jwt_token"
        expires_at = int(time.time()) + 3600  # 1 hora desde ahora

        # Act
        cookie_data = auth_service.get_session_cookie_data(session_token, expires_at)

        # Assert
        assert cookie_data.key == "session_token"
        assert cookie_data.value == session_token
        assert cookie_data.httponly is True
        assert cookie_data.secure is True
        assert cookie_data.samesite == "strict"
        assert cookie_data.max_age > 0

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, auth_service, sample_google_user_response):
        """Test de obtención de perfil de usuario."""
        # Arrange
        access_token = "test_access_token"
        user_info_data = {
            "id": sample_google_user_response["sub"],
            "email": sample_google_user_response["email"],
            "verified_email": sample_google_user_response["email_verified"],
            "name": sample_google_user_response["name"],
            "picture": sample_google_user_response["picture"],
        }
        
        auth_service.client.get_user_info = AsyncMock(return_value=user_info_data)
        auth_service.cache_service.get = AsyncMock(return_value=None)
        auth_service.cache_service.set = AsyncMock(return_value=True)

        # Act
        result = await auth_service.get_user_profile(access_token)

        # Assert
        assert result is not None
        assert result.sub == sample_google_user_response["sub"]
        assert result.email == sample_google_user_response["email"]
        auth_service.client.get_user_info.assert_called_once_with(access_token)

    @pytest.mark.asyncio
    async def test_get_user_profile_cache_hit(self, auth_service, sample_google_user_response):
        """Test de obtención de perfil de usuario con cache hit."""
        # Arrange
        access_token = "test_access_token"
        cached_data = sample_google_user_response
        
        auth_service.cache_service.get = AsyncMock(return_value=cached_data)

        # Act
        result = await auth_service.get_user_profile(access_token)

        # Assert
        assert result is not None
        assert result.sub == sample_google_user_response["sub"]
        # No debe llamar a get_user_info si hay cache
        auth_service.client.get_user_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_and_refresh_session_success(self, auth_service):
        """Test de validación de sesión exitosa sin refresh."""
        # Arrange
        session_token = "valid_session_token"
        user_sub = "test_user_sub"
        session_id = "test_session_id"
        
        # Mock JWT decode
        auth_service.jwt_service.decode = MagicMock(
            return_value={"sub": user_sub, "jti": session_id, "exp": int(time.time()) + 3600}
        )
        
        # Mock user aggregate with valid session
        user = UserAggregate.create(
            user_id=user_sub,
            email="test@example.com",
        )
        user.create_session(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=int(time.time()) + 1800,  # 30 minutos
            refresh_expires_at=int(time.time()) + 3600,  # 1 hora
            session_id=session_id,
        )
        
        auth_service.user_repo.find_by_id = AsyncMock(return_value=user)
        auth_service.user_repo.get_token_by_sub = AsyncMock(return_value=None)

        # Act
        result = await auth_service.validate_and_refresh_session(session_token)

        # Assert
        assert result["authenticated"] is True
        assert result["user_sub"] == user_sub
        assert result["token_refreshed"] is False

    @pytest.mark.asyncio
    async def test_validate_and_refresh_session_user_not_found(self, auth_service):
        """Test de validación de sesión cuando el usuario no existe."""
        # Arrange
        session_token = "valid_session_token"
        user_sub = "test_user_sub"
        session_id = "test_session_id"
        
        auth_service.jwt_service.decode = MagicMock(
            return_value={"sub": user_sub, "jti": session_id, "exp": int(time.time()) + 3600}
        )
        auth_service.user_repo.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        from src.core.exceptions import AuthenticationFailedError
        with pytest.raises(AuthenticationFailedError, match="User not found"):
            await auth_service.validate_and_refresh_session(session_token)

    @pytest.mark.asyncio
    async def test_logout_success(self, auth_service):
        """Test de logout exitoso."""
        # Arrange
        session: dict = {
            "user_sub": "test_user_sub",
            "access_token": "test_access_token",
            "session_id": "test_session_id",
        }
        
        auth_service.user_repo.delete = AsyncMock()
        auth_service.client.revoke_access_token = AsyncMock()

        # Act
        await auth_service.logout(session)

        # Assert
        auth_service.user_repo.delete.assert_called_once_with(session["user_sub"])
        auth_service.client.revoke_access_token.assert_called_once_with(
            session["access_token"]
        )

    @pytest.mark.asyncio
    async def test_logout_failure(self, auth_service):
        """Test de logout cuando falla."""
        # Arrange
        session: dict = {
            "user_sub": "test_user_sub",
            "access_token": "test_access_token",
            "session_id": "test_session_id",
        }
        
        auth_service.user_repo.delete = AsyncMock(side_effect=Exception("DB error"))

        # Act & Assert
        from src.core.exceptions import LogoutFailedError
        with pytest.raises(LogoutFailedError):
            await auth_service.logout(session)
