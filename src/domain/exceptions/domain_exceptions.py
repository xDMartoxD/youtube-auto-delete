"""Base domain exception."""


class DomainException(Exception):
    """Base exception for domain layer."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class SuggestionNotFoundDomainException(DomainException):
    """Domain exception raised when a suggestion is not found."""

    def __init__(self, message: str = "Suggestion not found") -> None:
        super().__init__(message)

