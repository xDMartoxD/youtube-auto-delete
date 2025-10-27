"""
Tests de integración para endpoints de autenticación.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


class TestAuthEndpoints:
    """Tests de integración para endpoints de auth."""

    def test_exchange_code_endpoint_success(
        self,
        client: TestClient,
        sample_google_auth_response,
        sample_google_user_response,
    ):
        """Test exitoso del endpoint de intercambio de código."""
        # Arrange
        request_data = {
            "code": "test_code",
            "redirect_uri": "http://localhost:3000/callback",
        }

        with patch("src.api.deps.get_auth_service") as mock_get_auth_service:
            mock_auth_service = AsyncMock()
            mock_auth_service.exchange_code = AsyncMock()
            mock_get_auth_service.return_value.__enter__.return_value = (
                mock_auth_service
            )

            # Act
            response = client.post("/api/auth/exchange", json=request_data)

            # Assert
            assert response.status_code == 200
            mock_auth_service.exchange_code.assert_called_once()

    def test_exchange_code_endpoint_invalid_data(self, client: TestClient):
        """Test con datos inválidos en el endpoint."""
        # Arrange
        request_data = {
            "code": "",  # Código vacío
            "redirect_uri": "http://localhost:3000/callback",
        }

        # Act
        response = client.post("/api/auth/exchange", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_exchange_code_endpoint_missing_fields(self, client: TestClient):
        """Test con campos faltantes."""
        # Arrange
        request_data = {
            "code": "test_code"
            # redirect_uri faltante
        }

        # Act
        response = client.post("/api/auth/exchange", json=request_data)

        # Assert
        assert response.status_code == 422  # Validation error
