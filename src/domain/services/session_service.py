"""Domain service for session business rules."""

from datetime import datetime, timezone

from src.domain.entities.session import Session
from src.domain.aggregates.user_aggregate import UserAggregate


class SessionService:
    """
    Domain service - contains ONLY business logic for sessions.
    Does NOT know how data is saved to DB or how APIs are called.
    """

    def should_refresh_token(
        self, session: Session, current_time: datetime | None = None
    ) -> bool:
        """
        Decides if a token should be refreshed.
        Business rule: refresh if access token is expired but refresh token is not.
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # If refresh token is expired, cannot refresh
        if session.is_fully_expired(current_time):
            return False

        # Refresh if access token is expired
        return session.needs_refresh(current_time)

    def is_session_expired(
        self, session: Session, current_time: datetime | None = None
    ) -> bool:
        """
        Checks if a session is completely expired.
        Business rule: both tokens must be expired.
        """
        return session.is_fully_expired(current_time)

    def validate_session(self, session: Session) -> Session:
        """
        Validates that a session is valid.
        Business rule: session must have a valid refresh token.
        """
        if not session.is_valid():
            raise ValueError("Session is expired")
        return session

    def can_refresh_session(self, user: UserAggregate) -> bool:
        """
        Checks if a user's session can be refreshed.
        Business rule: must have an active and valid session.
        """
        if not user.has_active_session():
            return False
        return user.get_session().is_valid()

