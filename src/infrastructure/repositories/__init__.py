"""Infrastructure repository implementations."""

from src.infrastructure.repositories.dynamodb_user_repository import DynamoDBUserRepository
from src.infrastructure.repositories.dynamodb_suggestion_repository import DynamoDBSuggestionRepository

__all__ = ["DynamoDBUserRepository", "DynamoDBSuggestionRepository"]

