"""Repository interfaces (ports) - domain defines contracts, infrastructure implements."""

from src.domain.repositories.user_repository import IUserRepository
from src.domain.repositories.suggestion_repository import ISuggestionRepository

__all__ = ["IUserRepository", "ISuggestionRepository"]

