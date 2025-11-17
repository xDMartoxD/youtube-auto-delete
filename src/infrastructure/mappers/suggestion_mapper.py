"""Mapper for converting between Suggestion entity and SuggestionModel."""

from datetime import datetime, timezone

from src.domain.entities.suggestion import Suggestion
from src.infrastructure.persistence.models.suggestion_model import SuggestionModel
from src.infrastructure.persistence.dynamodb.types import Types


class SuggestionMapper:
    """Mapper for converting between domain Suggestion and persistence SuggestionModel."""

    @staticmethod
    def to_domain(suggestion_model: SuggestionModel) -> Suggestion:
        """Convert SuggestionModel to Suggestion entity."""
        return Suggestion(
            id=suggestion_model.id,
            title=suggestion_model.title,
            description=suggestion_model.description,
            created_at=datetime.fromtimestamp(suggestion_model.created_at, tz=timezone.utc),
            updated_at=datetime.fromtimestamp(suggestion_model.updated_at, tz=timezone.utc),
        )

    @staticmethod
    def to_persistence(suggestion: Suggestion) -> SuggestionModel:
        """Convert Suggestion entity to SuggestionModel."""
        return SuggestionModel(
            PK=f"{Types.SUGGESTION.value}#{suggestion.id}",
            SK=Types.SUGGESTION.value,
            type=Types.SUGGESTION.value,
            id=suggestion.id,
            title=suggestion.title,
            description=suggestion.description,
            created_at=int(suggestion.created_at.timestamp()),
            updated_at=int(suggestion.updated_at.timestamp()),
        )
