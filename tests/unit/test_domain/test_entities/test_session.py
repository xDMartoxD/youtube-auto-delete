"""
Unit tests for Session entity.
"""

import pytest
from datetime import datetime, timezone
import time

from src.domain.entities.session import Session


class TestSession:
    """Tests for Session entity."""

    @pytest.fixture
    def valid_session(self):
        """Create a valid session."""
        current_time = int(time.time())
        return Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=current_time + 3600,  # 1 hour from now
            refresh_expires_at=current_time + 86400,  # 24 hours from now
            session_id="session_123"
        )

    @pytest.fixture
    def expired_access_token_session(self):
        """Create a session with expired access token but valid refresh token."""
        current_time = int(time.time())
        return Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=current_time - 100,  # Expired
            refresh_expires_at=current_time + 86400,  # Still valid
            session_id="session_123"
        )

    @pytest.fixture
    def fully_expired_session(self):
        """Create a fully expired session."""
        current_time = int(time.time())
        return Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=current_time - 100,  # Expired
            refresh_expires_at=current_time - 50,  # Also expired
            session_id="session_123"
        )

    def test_create_session(self):
        """Test creating a new session."""
        # Act
        session = Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=1234567890,
            refresh_expires_at=1234567890,
        )

        # Assert
        assert session.user_id == "test_user"
        assert session.access_token == "access_token"
        assert session.refresh_token == "refresh_token"
        assert session.expires_at == 1234567890
        assert session.refresh_expires_at == 1234567890
        assert session.session_id is None

    def test_create_session_with_session_id(self):
        """Test creating a session with session_id."""
        # Act
        session = Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=1234567890,
            refresh_expires_at=1234567890,
            session_id="session_123"
        )

        # Assert
        assert session.session_id == "session_123"

    def test_expiration_property(self, valid_session):
        """Test expiration property returns TokenExpiration value object."""
        # Act
        expiration = valid_session.expiration

        # Assert
        assert expiration.expires_at == valid_session.expires_at
        assert expiration.refresh_expires_at == valid_session.refresh_expires_at

    def test_needs_refresh_with_valid_token(self, valid_session):
        """Test needs_refresh returns False for valid token."""
        # Act
        result = valid_session.needs_refresh()

        # Assert
        assert result is False

    def test_needs_refresh_with_expired_access_token(self, expired_access_token_session):
        """Test needs_refresh returns True when access token is expired."""
        # Act
        result = expired_access_token_session.needs_refresh()

        # Assert
        assert result is True

    def test_is_fully_expired_with_valid_session(self, valid_session):
        """Test is_fully_expired returns False for valid session."""
        # Act
        result = valid_session.is_fully_expired()

        # Assert
        assert result is False

    def test_is_fully_expired_with_fully_expired_session(self, fully_expired_session):
        """Test is_fully_expired returns True when both tokens are expired."""
        # Act
        result = fully_expired_session.is_fully_expired()

        # Assert
        assert result is True

    def test_is_valid_with_valid_session(self, valid_session):
        """Test is_valid returns True for valid session."""
        # Act
        result = valid_session.is_valid()

        # Assert
        assert result is True

    def test_is_valid_with_expired_refresh_token(self, fully_expired_session):
        """Test is_valid returns False when refresh token is expired."""
        # Act
        result = fully_expired_session.is_valid()

        # Assert
        assert result is False

    def test_update_access_token_success(self, valid_session):
        """Test updating access token successfully."""
        # Arrange
        new_token = "new_access_token"
        new_expires_at = int(time.time()) + 7200

        # Act
        valid_session.update_access_token(new_token, new_expires_at)

        # Assert
        assert valid_session.access_token == new_token
        assert valid_session.expires_at == new_expires_at

    def test_update_access_token_with_expired_session_raises_error(self, fully_expired_session):
        """Test that updating access token on expired session raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot update access token: session is expired"):
            fully_expired_session.update_access_token("new_token", int(time.time()) + 3600)

    def test_is_valid_with_custom_time(self, valid_session):
        """Test is_valid with custom current time."""
        # Arrange
        future_time = datetime.now(timezone.utc).replace(year=2100)

        # Act
        result = valid_session.is_valid(future_time)

        # Assert
        assert result is False  # Session would be expired in 2100

