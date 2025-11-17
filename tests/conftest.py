"""
Configuración global de pytest para todos los tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from src.main import create_app
from src.infrastructure.external_services.google_client import GoogleClient
from src.infrastructure.repositories.dynamodb_user_repository import DynamoDBUserRepository


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Crear un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Crear una instancia de la aplicación para testing."""
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Crear un cliente de test para la aplicación."""
    return TestClient(app)


@pytest.fixture
def mock_google_client() -> AsyncMock:
    """Mock del GoogleClient para tests."""
    client = AsyncMock(spec=GoogleClient)
    return client


@pytest.fixture
def mock_user_repository() -> AsyncMock:
    """Mock del DynamoDBUserRepository para tests."""
    repo = AsyncMock(spec=DynamoDBUserRepository)
    return repo


@pytest.fixture
def sample_google_auth_response():
    """Datos de ejemplo para respuesta de autenticación de Google."""
    return {
        "access_token": "sample_access_token",
        "refresh_token": "sample_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "refresh_token_expires_in": 3600,
        "id_token": "sample_id_token",
    }


@pytest.fixture
def sample_google_user_response():
    """Datos de ejemplo para respuesta de usuario de Google."""
    return {
        "sub": "123456789",
        "email": "test@example.com",
        "email_verified": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/picture.jpg",
        "iss": "https://accounts.google.com",
        "aud": "test_client_id",
        "azp": "test_client_id",
        "iat": 1234567890,
        "exp": 1234571490,
    }


@pytest.fixture
def sample_session_validation():
    """Fixture para SessionValidation."""
    from datetime import datetime, timezone
    return {
        "authenticated": True,
        "user_sub": "test_user_sub",
        "session_id": "test_session_id",
        "access_token": "test_access_token",
        "token_refreshed": False,
        "new_session_token": None,
        "refresh_expires_at": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
