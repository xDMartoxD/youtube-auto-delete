"""
Unit tests for SessionService.
"""

import pytest
from datetime import datetime, timezone
import time

from src.domain.services.session_service import SessionService
from src.domain.entities.session import Session
from src.domain.aggregates.user_aggregate import UserAggregate


class TestSessionService:
    """Tests for SessionService."""

    @pytest.fixture
    def service(self):
        """Create SessionService instance."""
        return SessionService()

    @pytest.fixture
    def valid_session(self):
        """Create a valid session."""
        current_time = int(time.time())
        return Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )

    @pytest.fixture
    def expired_access_token_session(self):
        """Create session with expired access token."""
        current_time = int(time.time())
        return Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=current_time - 100,
            refresh_expires_at=current_time + 86400,
        )

    @pytest.fixture
    def fully_expired_session(self):
        """Create fully expired session."""
        current_time = int(time.time())
        return Session.create(
            user_id="test_user",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=current_time - 100,
            refresh_expires_at=current_time - 50,
        )

    def test_should_refresh_token_with_valid_token(self, service, valid_session):
        """Test should_refresh_token returns False for valid token."""
        # Act
        result = service.should_refresh_token(valid_session)

        # Assert
        assert result is False

    def test_should_refresh_token_with_expired_access_token(self, service, expired_access_token_session):
        """Test should_refresh_token returns True when access token is expired."""
        # Act
        result = service.should_refresh_token(expired_access_token_session)

        # Assert
        assert result is True

    def test_should_refresh_token_with_fully_expired_session(self, service, fully_expired_session):
        """Test should_refresh_token returns False when both tokens are expired."""
        # Act
        result = service.should_refresh_token(fully_expired_session)

        # Assert
        assert result is False

    def test_is_session_expired_with_valid_session(self, service, valid_session):
        """Test is_session_expired returns False for valid session."""
        # Act
        result = service.is_session_expired(valid_session)

        # Assert
        assert result is False

    def test_is_session_expired_with_expired_session(self, service, fully_expired_session):
        """Test is_session_expired returns True for expired session."""
        # Act
        result = service.is_session_expired(fully_expired_session)

        # Assert
        assert result is True

    def test_validate_session_with_valid_session(self, service, valid_session):
        """Test validate_session returns session for valid session."""
        # Act
        result = service.validate_session(valid_session)

        # Assert
        assert result == valid_session

    def test_validate_session_with_expired_session_raises_error(self, service, fully_expired_session):
        """Test validate_session raises ValueError for expired session."""
        # Act & Assert
        with pytest.raises(ValueError, match="Session is expired"):
            service.validate_session(fully_expired_session)

    def test_can_refresh_session_with_active_session(self, service):
        """Test can_refresh_session returns True for user with active session."""
        # Arrange
        user = UserAggregate.create("user_id", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )

        # Act
        result = service.can_refresh_session(user)

        # Assert
        assert result is True

    def test_can_refresh_session_without_session(self, service):
        """Test can_refresh_session returns False for user without session."""
        # Arrange
        user = UserAggregate.create("user_id", "test@example.com")

        # Act
        result = service.can_refresh_session(user)

        # Assert
        assert result is False

    def test_can_refresh_session_with_expired_session(self, service):
        """Test can_refresh_session returns False for user with expired session."""
        # Arrange
        user = UserAggregate.create("user_id", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time - 100,
            refresh_expires_at=current_time - 50,
        )

        # Act
        result = service.can_refresh_session(user)

        # Assert
        assert result is False

