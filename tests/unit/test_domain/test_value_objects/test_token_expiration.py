"""
Unit tests for TokenExpiration value object.
"""

import pytest
from datetime import datetime, timezone
import time

from src.domain.value_objects.token_expiration import TokenExpiration


class TestTokenExpiration:
    """Tests for TokenExpiration value object."""

    def test_create_valid_token_expiration(self):
        """Test creating a valid TokenExpiration."""
        # Arrange
        current_time = int(time.time())
        expires_at = current_time + 3600
        refresh_expires_at = current_time + 86400

        # Act
        expiration = TokenExpiration(
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at
        )

        # Assert
        assert expiration.expires_at == expires_at
        assert expiration.refresh_expires_at == refresh_expires_at

    def test_create_invalid_expires_at_raises_error(self):
        """Test that invalid expires_at raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="expires_at must be a positive timestamp"):
            TokenExpiration(expires_at=0, refresh_expires_at=1000)

    def test_create_invalid_refresh_expires_at_raises_error(self):
        """Test that invalid refresh_expires_at raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="refresh_expires_at must be a positive timestamp"):
            TokenExpiration(expires_at=1000, refresh_expires_at=0)

    def test_create_refresh_before_expires_raises_error(self):
        """Test that refresh_expires_at < expires_at raises ValueError."""
        # Arrange
        current_time = int(time.time())

        # Act & Assert
        with pytest.raises(ValueError, match="refresh_expires_at must be >= expires_at"):
            TokenExpiration(
                expires_at=current_time + 86400,
                refresh_expires_at=current_time + 3600
            )

    def test_is_expired_with_valid_token(self):
        """Test is_expired returns False for valid token."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400
        )

        # Act
        result = expiration.is_expired()

        # Assert
        assert result is False

    def test_is_expired_with_expired_token(self):
        """Test is_expired returns True for expired token."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time - 100,
            refresh_expires_at=current_time + 86400
        )

        # Act
        result = expiration.is_expired()

        # Assert
        assert result is True

    def test_is_expired_with_custom_time(self):
        """Test is_expired with custom current time."""
        # Arrange
        expiration = TokenExpiration(
            expires_at=1000,
            refresh_expires_at=2000
        )
        future_time = datetime.now(timezone.utc).replace(year=2100)

        # Act
        result = expiration.is_expired(future_time)

        # Assert
        assert result is True

    def test_is_refresh_expired_with_valid_token(self):
        """Test is_refresh_expired returns False for valid refresh token."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400
        )

        # Act
        result = expiration.is_refresh_expired()

        # Assert
        assert result is False

    def test_is_refresh_expired_with_expired_token(self):
        """Test is_refresh_expired returns True for expired refresh token."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time - 100,
            refresh_expires_at=current_time - 50
        )

        # Act
        result = expiration.is_refresh_expired()

        # Assert
        assert result is True

    def test_is_fully_expired_with_valid_tokens(self):
        """Test is_fully_expired returns False when tokens are valid."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400
        )

        # Act
        result = expiration.is_fully_expired()

        # Assert
        assert result is False

    def test_is_fully_expired_with_fully_expired_tokens(self):
        """Test is_fully_expired returns True when both tokens are expired."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time - 100,
            refresh_expires_at=current_time - 50
        )

        # Act
        result = expiration.is_fully_expired()

        # Assert
        assert result is True

    def test_time_until_expiry_with_valid_token(self):
        """Test time_until_expiry returns positive value for valid token."""
        # Arrange
        current_time = int(time.time())
        expires_at = current_time + 3600
        expiration = TokenExpiration(
            expires_at=expires_at,
            refresh_expires_at=current_time + 86400
        )

        # Act
        result = expiration.time_until_expiry()

        # Assert
        assert result > 0
        assert result <= 3600  # Should be close to 3600

    def test_time_until_expiry_with_expired_token(self):
        """Test time_until_expiry returns negative value for expired token."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time - 100,
            refresh_expires_at=current_time + 86400
        )

        # Act
        result = expiration.time_until_expiry()

        # Assert
        assert result < 0

    def test_is_immutable(self):
        """Test that TokenExpiration is immutable (frozen dataclass)."""
        # Arrange
        current_time = int(time.time())
        expiration = TokenExpiration(
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400
        )

        # Act & Assert
        with pytest.raises(Exception):  # FrozenInstanceError
            expiration.expires_at = current_time + 7200

