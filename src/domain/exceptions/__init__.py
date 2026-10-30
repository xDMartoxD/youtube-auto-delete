"""Domain exceptions - business logic exceptions."""

from src.domain.exceptions.domain_exceptions import (
    DomainException,
    PlaylistNotFoundDomainException,
    SuggestionNotFoundDomainException,
)

__all__ = [
    "DomainException",
    "PlaylistNotFoundDomainException",
    "SuggestionNotFoundDomainException",
]

