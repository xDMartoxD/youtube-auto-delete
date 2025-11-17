"""
Unit tests for UserAggregate.
"""

import pytest
import time
from datetime import datetime, timezone

from src.domain.aggregates.user_aggregate import UserAggregate
from src.domain.value_objects.email import Email
from src.domain.entities.session import Session


class TestUserAggregate:
    """Tests for UserAggregate."""

    def test_create_user_aggregate(self):
        """Test creating a new user aggregate."""
        # Act
        user = UserAggregate.create(
            user_id="user123",
            email="test@example.com",
            name="Test User",
            picture="https://example.com/pic.jpg"
        )

        # Assert
        assert user.user_id == "user123"
        assert isinstance(user.email, Email)
        assert user.email.value == "test@example.com"
        assert user.name == "Test User"
        assert user.picture == "https://example.com/pic.jpg"
        assert user.session is None

    def test_create_user_aggregate_with_email_object(self):
        """Test creating user with Email value object."""
        # Arrange
        email = Email("test@example.com")

        # Act
        user = UserAggregate.create(
            user_id="user123",
            email=email
        )

        # Assert
        assert user.email == email

    def test_create_session(self):
        """Test creating a session for user."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())

        # Act
        session = user.create_session(
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
            session_id="session_123"
        )

        # Assert
        assert user.session is not None
        assert user.session == session
        assert session.user_id == "user123"
        assert session.session_id == "session_123"

    def test_create_session_replaces_existing(self):
        """Test that creating a new session replaces existing one."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="old_token",
            refresh_token="old_refresh",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )

        # Act
        new_session = user.create_session(
            access_token="new_token",
            refresh_token="new_refresh",
            expires_at=current_time + 7200,
            refresh_expires_at=current_time + 172800,
        )

        # Assert
        assert user.session == new_session
        assert user.session.access_token == "new_token"

    def test_refresh_session_success(self):
        """Test refreshing session successfully."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="old_token",
            refresh_token="refresh_token",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )

        # Act
        user.refresh_session("new_token", current_time + 7200)

        # Assert
        assert user.session.access_token == "new_token"
        assert user.session.expires_at == current_time + 7200

    def test_refresh_session_without_session_raises_error(self):
        """Test that refreshing without session raises ValueError."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot refresh: no active session"):
            user.refresh_session("new_token", int(time.time()) + 3600)

    def test_refresh_session_with_expired_session_raises_error(self):
        """Test that refreshing expired session raises ValueError."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time - 100,
            refresh_expires_at=current_time - 50,  # Expired
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot refresh: session is expired"):
            user.refresh_session("new_token", current_time + 3600)

    def test_end_session(self):
        """Test ending a session."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )

        # Act
        user.end_session()

        # Assert
        assert user.session is None

    def test_has_active_session_with_valid_session(self):
        """Test has_active_session returns True for valid session."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )

        # Act
        result = user.has_active_session()

        # Assert
        assert result is True

    def test_has_active_session_without_session(self):
        """Test has_active_session returns False without session."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")

        # Act
        result = user.has_active_session()

        # Assert
        assert result is False

    def test_has_active_session_with_expired_session(self):
        """Test has_active_session returns False for expired session."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())
        user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time - 100,
            refresh_expires_at=current_time - 50,
        )

        # Act
        result = user.has_active_session()

        # Assert
        assert result is False

    def test_get_session_with_valid_session(self):
        """Test get_session returns session when it exists."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")
        current_time = int(time.time())
        session = user.create_session(
            access_token="token",
            refresh_token="refresh",
            expires_at=current_time + 3600,
            refresh_expires_at=current_time + 86400,
        )

        # Act
        result = user.get_session()

        # Assert
        assert result == session

    def test_get_session_without_session_raises_error(self):
        """Test get_session raises ValueError when no session exists."""
        # Arrange
        user = UserAggregate.create("user123", "test@example.com")

        # Act & Assert
        with pytest.raises(ValueError, match="User has no active session"):
            user.get_session()

