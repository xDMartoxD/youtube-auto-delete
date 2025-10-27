"""
Tests unitarios para AuthService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Response

from src.domain.services.auth import AuthService
from src.domain.schemas.auth import GoogleAuthResponse
from src.domain.schemas.user import GoogleUserResponse
from src.db.models.auth import TokenModel
from src.db.models.user import UserModel


class TestAuthService:
    """Tests para AuthService."""

    @pytest.fixture
    def auth_service(
        self, mock_google_client, mock_auth_repository, mock_user_repository
    ):
        """Crear instancia de AuthService para testing."""
        return AuthService(
            client=mock_google_client,
            auth_repo=mock_auth_repository,
            user_repo=mock_user_repository,
        )

    @pytest.mark.asyncio
    async def test_exchange_code_success(
        self, auth_service, sample_google_auth_response, sample_google_user_response
    ):
        """Test exitoso del intercambio de código."""
        # Arrange
        code = "test_code"
        redirect_uri = "http://localhost:3000/callback"
        response = MagicMock(spec=Response)

        auth_service.client.exchange_code.return_value = GoogleAuthResponse(
            **sample_google_auth_response
        )
        auth_service.client.decode_id_token.return_value = GoogleUserResponse(
            **sample_google_user_response
        )
        auth_service.auth_repo.insert = AsyncMock()
        auth_service.user_repo.insert = AsyncMock()

        # Act
        user_data, session_token = await auth_service.exchange_code(code, redirect_uri)

        # Assert
        auth_service.client.exchange_code.assert_called_once_with(code, redirect_uri)
        auth_service.client.decode_id_token.assert_called_once()
        auth_service.auth_repo.insert.assert_called_once()
        auth_service.user_repo.insert.assert_called_once()

        # Verificar que retorna los datos del usuario y token
        assert user_data is not None
        assert user_data.sub == sample_google_user_response["sub"]
        assert user_data.email == sample_google_user_response["email"]
        assert session_token is not None
        assert isinstance(session_token, str)

    @pytest.mark.asyncio
    async def test_exchange_code_google_client_error(self, auth_service):
        """Test cuando el cliente de Google falla."""
        # Arrange
        code = "invalid_code"
        redirect_uri = "http://localhost:3000/callback"
        response = MagicMock(spec=Response)

        auth_service.client.exchange_code.side_effect = Exception("Google API error")

        # Act & Assert
        with pytest.raises(Exception):
            await auth_service.exchange_code(code, redirect_uri, response)

    @pytest.mark.asyncio
    async def test_persist_user_data_atomically_success(self, auth_service):
        """Test de persistencia atómica exitosa."""
        # Arrange
        token_model = MagicMock(spec=TokenModel)
        user_model = MagicMock(spec=UserModel)
        user_model.sub = "test_sub"
        user_model.email = "test@example.com"

        auth_service.auth_repo.insert = AsyncMock()
        auth_service.user_repo.insert = AsyncMock()

        # Act
        await auth_service._persist_user_data_atomically(token_model, user_model)

        # Assert
        auth_service.auth_repo.insert.assert_called_once_with(token_model)
        auth_service.user_repo.insert.assert_called_once_with(user_model)

    @pytest.mark.asyncio
    async def test_persist_user_data_atomically_failure(self, auth_service):
        """Test de fallo en persistencia atómica."""
        # Arrange
        token_model = MagicMock(spec=TokenModel)
        user_model = MagicMock(spec=UserModel)
        user_model.sub = "test_sub"
        user_model.email = "test@example.com"

        auth_service.auth_repo.insert = AsyncMock(side_effect=Exception("DB error"))

        # Act & Assert
        with pytest.raises(Exception):
            await auth_service._persist_user_data_atomically(token_model, user_model)

    def test_generate_session_token(self, auth_service):
        """Test de generación de token de sesión."""
        # Arrange
        sub = "test_sub"

        # Act
        token = auth_service._generate_session_token(sub)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        # El token debería ser un JWT válido (contiene puntos)
        assert "." in token

    def test_set_session_cookie(self, auth_service):
        """Test de establecimiento de cookie de sesión."""
        # Arrange
        response = MagicMock(spec=Response)
        session_token = "test_jwt_token"

        # Act
        auth_service.set_session_cookie(response, session_token)

        # Assert
        response.set_cookie.assert_called_once()

        # Verificar parámetros de la cookie
        call_args = response.set_cookie.call_args
        assert call_args[1]["key"] == "session_token"
        assert call_args[1]["value"] == session_token
        assert call_args[1]["httponly"] is True
        assert call_args[1]["secure"] is True
        assert call_args[1]["samesite"] == "strict"
