"""Application service for suggestions - orchestrates domain and infrastructure."""

import logging

from src.domain.entities.suggestion import Suggestion
from src.domain.services.suggestion_service import SuggestionService
from src.domain.repositories.suggestion_repository import ISuggestionRepository
from src.domain.events.suggestion_created import SuggestionCreated
from src.domain.exceptions.domain_exceptions import SuggestionNotFoundDomainException
from src.core.exceptions import SuggestionNotFoundError
from src.schemas.suggestions import (
    SuggestionCreate,
    SuggestionUpdate,
    SuggestionResponse,
    SuggestionListResponse,
)

logger = logging.getLogger(__name__)


class SuggestionsService:
    """
    Application service - orchestrates domain and infrastructure.
    Does NOT contain business logic, only orchestrates.
    """

    def __init__(
        self,
        suggestion_repo: ISuggestionRepository,
        suggestion_service: SuggestionService | None = None,
    ):
        self.suggestion_repo = suggestion_repo
        self.suggestion_service = suggestion_service or SuggestionService()

    def _to_response(self, suggestion: Suggestion) -> SuggestionResponse:
        """Converts a domain entity to a response schema."""
        return SuggestionResponse(
            id=suggestion.id,
            title=suggestion.title,
            description=suggestion.description,
            created_at=suggestion.created_at,
            updated_at=suggestion.updated_at,
        )

    async def create_suggestion(
        self, suggestion_data: SuggestionCreate
    ) -> SuggestionResponse:
        """Creates a new suggestion."""
        # DOMAIN: Create entity
        suggestion = Suggestion.create(
            title=suggestion_data.title,
            description=suggestion_data.description,
        )

        # INFRASTRUCTURE: Save to database
        await self.suggestion_repo.save(suggestion)

        # DOMAIN: Raise domain event
        event = SuggestionCreated(
            suggestion_id=suggestion.id,
            title=suggestion.title,
        )
        logger.info(f"Domain event: {event}")

        logger.info(f"Suggestion created: {suggestion.id}")
        return self._to_response(suggestion)

    async def get_suggestion(self, suggestion_id: str) -> SuggestionResponse:
        """Gets a suggestion by its ID."""
        # INFRASTRUCTURE: Get from database
        suggestion = await self.suggestion_repo.find_by_id(suggestion_id)

        # DOMAIN: Validate that it exists (may raise SuggestionNotFoundDomainException)
        try:
            suggestion = self.suggestion_service.validate_suggestion_exists(suggestion)
        except SuggestionNotFoundDomainException as e:
            # Map domain exception to application exception
            raise SuggestionNotFoundError(
                message=str(e.message),
                user_message="Suggestion not found",
            ) from e

        return self._to_response(suggestion)

    async def get_all_suggestions(self) -> SuggestionListResponse:
        """Gets all suggestions."""
        # INFRASTRUCTURE: Get from database
        suggestions = await self.suggestion_repo.find_all()

        suggestion_responses = [self._to_response(s) for s in suggestions]

        return SuggestionListResponse(
            items=suggestion_responses,
            total=len(suggestion_responses),
        )

    async def update_suggestion(
        self, suggestion_id: str, suggestion_data: SuggestionUpdate
    ) -> SuggestionResponse:
        """Updates a suggestion."""
        # INFRASTRUCTURE: Get from database
        suggestion = await self.suggestion_repo.find_by_id(suggestion_id)

        # DOMAIN: Validate that it exists (may raise SuggestionNotFoundDomainException)
        try:
            suggestion = self.suggestion_service.validate_suggestion_exists(suggestion)
        except SuggestionNotFoundDomainException as e:
            # Map domain exception to application exception
            raise SuggestionNotFoundError(
                message=str(e.message),
                user_message="Suggestion not found",
            ) from e

        # DOMAIN: Validate that it can be updated
        if not self.suggestion_service.can_update(suggestion):
            raise ValueError("Suggestion cannot be updated")

        # DOMAIN: Update entity
        if suggestion_data.title is not None or suggestion_data.description is not None:
            suggestion.update(
                title=suggestion_data.title,
                description=suggestion_data.description,
            )

            # INFRASTRUCTURE: Save changes
            await self.suggestion_repo.save(suggestion)

        logger.info(f"Suggestion updated: {suggestion_id}")
        return self._to_response(suggestion)

    async def delete_suggestion(self, suggestion_id: str) -> None:
        """Deletes a suggestion."""
        # INFRASTRUCTURE: Get from database
        suggestion = await self.suggestion_repo.find_by_id(suggestion_id)

        # DOMAIN: Validate that it exists and can be deleted (may raise SuggestionNotFoundDomainException)
        try:
            suggestion = self.suggestion_service.validate_suggestion_exists(suggestion)
        except SuggestionNotFoundDomainException as e:
            # Map domain exception to application exception
            raise SuggestionNotFoundError(
                message=str(e.message),
                user_message="Suggestion not found",
            ) from e
        if not self.suggestion_service.can_delete(suggestion):
            raise ValueError("Suggestion cannot be deleted")

        # INFRASTRUCTURE: Delete from database
        await self.suggestion_repo.delete(suggestion_id)
        logger.info(f"Suggestion deleted: {suggestion_id}")

