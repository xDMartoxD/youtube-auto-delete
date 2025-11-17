"""
Unit tests for Email value object.
"""

import pytest

from src.domain.value_objects.email import Email


class TestEmail:
    """Tests for Email value object."""

    def test_create_valid_email(self):
        """Test creating a valid email."""
        # Act
        email = Email("test@example.com")

        # Assert
        assert email.value == "test@example.com"
        assert str(email) == "test@example.com"

    def test_create_email_with_subdomain(self):
        """Test creating email with subdomain."""
        # Act
        email = Email("user@mail.example.com")

        # Assert
        assert email.value == "user@mail.example.com"

    def test_create_email_with_plus(self):
        """Test creating email with plus sign."""
        # Act
        email = Email("user+tag@example.com")

        # Assert
        assert email.value == "user+tag@example.com"

    def test_create_email_with_dots(self):
        """Test creating email with dots."""
        # Act
        email = Email("first.last@example.com")

        # Assert
        assert email.value == "first.last@example.com"

    def test_create_invalid_email_no_at(self):
        """Test that invalid email without @ raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("invalidemail.com")

    def test_create_invalid_email_no_domain(self):
        """Test that invalid email without domain raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("user@")

    def test_create_invalid_email_no_local_part(self):
        """Test that invalid email without local part raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            Email("@example.com")

    def test_create_empty_email_raises_error(self):
        """Test that empty email raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Email must be a non-empty string"):
            Email("")

    def test_create_none_email_raises_error(self):
        """Test that None email raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Email must be a non-empty string"):
            Email(None)  # type: ignore

    def test_create_email_too_long_raises_error(self):
        """Test that email > 254 chars raises ValueError."""
        # Arrange
        long_local = "a" * 250
        long_email = f"{long_local}@example.com"

        # Act & Assert
        with pytest.raises(ValueError, match="Email address too long"):
            Email(long_email)

    def test_email_domain_property(self):
        """Test domain property extracts domain correctly."""
        # Arrange
        email = Email("user@example.com")

        # Act
        domain = email.domain

        # Assert
        assert domain == "example.com"

    def test_email_local_part_property(self):
        """Test local_part property extracts local part correctly."""
        # Arrange
        email = Email("user@example.com")

        # Act
        local_part = email.local_part

        # Assert
        assert local_part == "user"

    def test_email_is_immutable(self):
        """Test that Email is immutable (frozen dataclass)."""
        # Arrange
        email = Email("test@example.com")

        # Act & Assert
        with pytest.raises(Exception):  # FrozenInstanceError
            email.value = "new@example.com"

    def test_email_repr(self):
        """Test email representation."""
        # Arrange
        email = Email("test@example.com")

        # Act
        repr_str = repr(email)

        # Assert
        assert "Email" in repr_str
        assert "test@example.com" in repr_str

