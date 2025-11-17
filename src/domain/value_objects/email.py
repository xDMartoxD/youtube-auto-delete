"""Value object for email addresses."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Email:
    """Value object representing an email address with validation."""

    value: str

    # RFC 5322 simplified regex
    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    def __post_init__(self) -> None:
        """Validate email format."""
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Email must be a non-empty string")
        if not self.EMAIL_REGEX.match(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
        if len(self.value) > 254:  # RFC 5321 limit
            raise ValueError("Email address too long (max 254 characters)")

    def __str__(self) -> str:
        """Return email as string."""
        return self.value

    def __repr__(self) -> str:
        """Return email representation."""
        return f"Email('{self.value}')"

    @property
    def domain(self) -> str:
        """Extract domain from email."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part from email."""
        return self.value.split("@")[0]

