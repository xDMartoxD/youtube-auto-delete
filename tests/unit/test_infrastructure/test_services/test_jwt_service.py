"""
Unit tests for JWTService.
"""

import pytest
import time
import jwt

from src.infrastructure.services.jwt_service import JWTService
from src.core.exceptions import AuthenticationFailedError


class TestJWTService:
    """Tests for JWTService."""

    @pytest.fixture
    def service(self):
        """Create JWTService instance."""
        return JWTService()

    def test_encode_creates_valid_jwt(self, service):
        """Test that encode creates a valid JWT."""
        # Arrange
        user_id = "user123"
        expires_at = int(time.time()) + 3600

        # Act
        token = service.encode(user_id=user_id, expires_at=expires_at)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        assert "." in token  # JWT format: header.payload.signature

    def test_encode_includes_user_id(self, service):
        """Test that encoded token includes user_id in payload."""
        # Arrange
        user_id = "user123"
        expires_at = int(time.time()) + 3600

        # Act
        token = service.encode(user_id=user_id, expires_at=expires_at)

        # Assert
        decoded = jwt.decode(token, "jwt_secret", algorithms=["HS256"])
        assert decoded["sub"] == user_id

    def test_encode_generates_session_id_if_not_provided(self, service):
        """Test that encode generates session_id if not provided."""
        # Arrange
        user_id = "user123"
        expires_at = int(time.time()) + 3600

        # Act
        token = service.encode(user_id=user_id, expires_at=expires_at)

        # Assert
        decoded = jwt.decode(token, "jwt_secret", algorithms=["HS256"])
        assert "jti" in decoded
        assert decoded["jti"] is not None

    def test_encode_uses_provided_session_id(self, service):
        """Test that encode uses provided session_id."""
        # Arrange
        user_id = "user123"
        session_id = "custom_session_123"
        expires_at = int(time.time()) + 3600

        # Act
        token = service.encode(user_id=user_id, expires_at=expires_at, session_id=session_id)

        # Assert
        decoded = jwt.decode(token, "jwt_secret", algorithms=["HS256"])
        assert decoded["jti"] == session_id

    def test_encode_includes_timestamps(self, service):
        """Test that encode includes iat and exp."""
        # Arrange
        user_id = "user123"
        expires_at = int(time.time()) + 3600
        issued_at = int(time.time())

        # Act
        token = service.encode(user_id=user_id, expires_at=expires_at, issued_at=issued_at)

        # Assert
        decoded = jwt.decode(token, "jwt_secret", algorithms=["HS256"])
        assert decoded["iat"] == issued_at
        assert decoded["exp"] == expires_at

    def test_decode_valid_token(self, service):
        """Test decoding a valid token."""
        # Arrange
        user_id = "user123"
        expires_at = int(time.time()) + 3600
        token = service.encode(user_id=user_id, expires_at=expires_at)

        # Act
        payload = service.decode(token)

        # Assert
        assert payload["sub"] == user_id
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_expired_token_raises_error(self, service):
        """Test that decoding expired token raises AuthenticationFailedError."""
        # Arrange
        user_id = "user123"
        expires_at = int(time.time()) - 100  # Expired
        token = service.encode(user_id=user_id, expires_at=expires_at)

        # Act & Assert
        with pytest.raises(AuthenticationFailedError, match="Session token expired"):
            service.decode(token)

    def test_decode_invalid_token_raises_error(self, service):
        """Test that decoding invalid token raises AuthenticationFailedError."""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act & Assert
        with pytest.raises(AuthenticationFailedError, match="Invalid session token"):
            service.decode(invalid_token)

    def test_decode_token_with_wrong_secret_raises_error(self, service):
        """Test that decoding token with wrong secret raises error."""
        # Arrange
        # Create token with different secret
        payload = {"sub": "user123", "exp": int(time.time()) + 3600}
        wrong_token = jwt.encode(payload, "wrong_secret", algorithm="HS256")

        # Act & Assert
        with pytest.raises(AuthenticationFailedError):
            service.decode(wrong_token)

    def test_encode_decode_roundtrip(self, service):
        """Test that encode/decode roundtrip works correctly."""
        # Arrange
        user_id = "user123"
        session_id = "session_456"
        expires_at = int(time.time()) + 3600
        issued_at = int(time.time())

        # Act
        token = service.encode(
            user_id=user_id,
            expires_at=expires_at,
            session_id=session_id,
            issued_at=issued_at
        )
        payload = service.decode(token)

        # Assert
        assert payload["sub"] == user_id
        assert payload["jti"] == session_id
        assert payload["exp"] == expires_at
        assert payload["iat"] == issued_at

