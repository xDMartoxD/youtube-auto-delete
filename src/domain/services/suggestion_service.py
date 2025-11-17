"""Domain service for suggestion business rules."""

from src.domain.entities.suggestion import Suggestion
from src.domain.exceptions.domain_exceptions import SuggestionNotFoundDomainException


class SuggestionService:
    """Domain service - contains ONLY business logic for suggestions."""

    def validate_suggestion_exists(
        self, suggestion: Suggestion | None
    ) -> Suggestion:
        """
        Validates that a suggestion exists.
        Raises SuggestionNotFoundDomainException if it doesn't exist.
        """
        if suggestion is None:
            raise SuggestionNotFoundDomainException("Suggestion not found")
        return suggestion

    def can_update(self, suggestion: Suggestion) -> bool:
        """
        Checks if a suggestion can be updated.
        Business rule: all suggestions can be updated.
        """
        return True

    def can_delete(self, suggestion: Suggestion) -> bool:
        """
        Checks if a suggestion can be deleted.
        Business rule: all suggestions can be deleted.
        """
        return True

