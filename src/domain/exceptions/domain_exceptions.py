"""Base domain exception."""


class DomainException(Exception):
    """Base exception for domain layer."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class PlaylistNotFoundDomainException(DomainException):
    """Domain exception raised when a playlist does not exist on a provider."""

    def __init__(self, playlist_id: str) -> None:
        super().__init__(f"Playlist {playlist_id} not found")


class SuggestionNotFoundDomainException(DomainException):
    """Domain exception raised when a suggestion is not found."""

    def __init__(self, message: str = "Suggestion not found") -> None:
        super().__init__(message)

