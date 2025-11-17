"""User aggregate - encapsulates User and Session with business invariants."""

from dataclasses import dataclass
from typing import Self

from src.domain.entities.session import Session
from src.domain.value_objects.email import Email


@dataclass(slots=True, frozen=False)
class UserAggregate:
    """
    Aggregate that encapsulates User and Session.
    Ensures business invariants:
    - A user can only have one active session
    - The session must be associated with the correct user
    """

    user_id: str
    email: Email
    name: str | None
    picture: str | None
    session: Session | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        email: str | Email,
        name: str | None = None,
        picture: str | None = None,
    ) -> Self:
        """Create a new user aggregate."""
        email_vo = email if isinstance(email, Email) else Email(email)
        return cls(
            user_id=user_id,
            email=email_vo,
            name=name,
            picture=picture,
            session=None,
        )

    def create_session(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        refresh_expires_at: int,
        session_id: str | None = None,
    ) -> Session:
        """
        Create a new session for the user.
        Invariant: If a session already exists, it is replaced.
        """
        self.session = Session.create(
            user_id=self.user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            session_id=session_id,
        )
        return self.session

    def refresh_session(self, new_access_token: str, new_expires_at: int) -> None:
        """
        Refresh the user's session.
        Invariant: Can only refresh if session exists and is valid.
        """
        if not self.session:
            raise ValueError("Cannot refresh: no active session")
        if not self.session.is_valid():
            raise ValueError("Cannot refresh: session is expired")

        self.session.update_access_token(new_access_token, new_expires_at)

    def end_session(self) -> None:
        """End the user's session."""
        self.session = None

    def has_active_session(self) -> bool:
        """Check if user has an active session."""
        return self.session is not None and self.session.is_valid()

    def get_session(self) -> Session:
        """Get the user's session. Raises if no session exists."""
        if not self.session:
            raise ValueError("User has no active session")
        return self.session
