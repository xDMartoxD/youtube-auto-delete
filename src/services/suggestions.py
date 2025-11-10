import logging
from src.db.models.suggestions import SuggestionModel
from src.db.repositories.suggestions import SuggestionsRepository
from src.schemas.suggestions import (
    SuggestionCreate,
    SuggestionUpdate,
    SuggestionResponse,
    SuggestionListResponse,
)
from src.core.exceptions import SuggestionNotFoundError

logger = logging.getLogger(__name__)


class SuggestionsService:
    """Servicio para gestionar sugerencias."""

    def __init__(self, suggestions_repo: SuggestionsRepository):
        self.suggestions_repo = suggestions_repo

    async def create_suggestion(
        self, suggestion_data: SuggestionCreate
    ) -> SuggestionResponse:
        """Crea una nueva sugerencia."""
        suggestion_model = SuggestionModel.create(
            title=suggestion_data.title,
            description=suggestion_data.description,
        )

        await self.suggestions_repo.insert(suggestion_model)

        logger.info(f"Sugerencia creada: {suggestion_model.id}")
        return SuggestionResponse(**suggestion_model.to_dict())

    async def get_suggestion(self, suggestion_id: str) -> SuggestionResponse:
        """Obtiene una sugerencia por su ID."""
        suggestion = await self.suggestions_repo.get_by_id(suggestion_id)

        if not suggestion:
            raise SuggestionNotFoundError(
                message=f"Suggestion with id {suggestion_id} not found",
                user_message="Sugerencia no encontrada",
            )

        return SuggestionResponse(**suggestion.to_dict())

    async def get_all_suggestions(self) -> SuggestionListResponse:
        """Obtiene todas las sugerencias."""
        suggestions = await self.suggestions_repo.get_all()
        suggestion_responses = [SuggestionResponse(**s.to_dict()) for s in suggestions]

        return SuggestionListResponse(
            items=suggestion_responses,
            total=len(suggestion_responses),
        )

    async def update_suggestion(
        self, suggestion_id: str, suggestion_data: SuggestionUpdate
    ) -> SuggestionResponse:
        """Actualiza una sugerencia."""
        # Verificar que existe
        existing = await self.suggestions_repo.get_by_id(suggestion_id)
        if not existing:
            raise SuggestionNotFoundError(
                message=f"Suggestion with id {suggestion_id} not found",
                user_message="Sugerencia no encontrada",
            )

        # Preparar datos de actualización (solo campos no None)
        update_data = {}
        if suggestion_data.title is not None:
            update_data["title"] = suggestion_data.title
        if suggestion_data.description is not None:
            update_data["description"] = suggestion_data.description

        if not update_data:
            # Si no hay nada que actualizar, retornar la sugerencia existente
            return SuggestionResponse(**existing.to_dict())

        # Actualizar
        updated = await self.suggestions_repo.update_suggestion(
            suggestion_id, update_data
        )

        if not updated:
            raise SuggestionNotFoundError(
                message=f"Suggestion with id {suggestion_id} not found after update",
                user_message="Error al actualizar la sugerencia",
            )

        logger.info(f"Sugerencia actualizada: {suggestion_id}")
        return SuggestionResponse(**updated.to_dict())

    async def delete_suggestion(self, suggestion_id: str) -> None:
        """Elimina una sugerencia."""
        # Verificar que existe
        existing = await self.suggestions_repo.get_by_id(suggestion_id)
        if not existing:
            raise SuggestionNotFoundError(
                message=f"Suggestion with id {suggestion_id} not found",
                user_message="Sugerencia no encontrada",
            )

        await self.suggestions_repo.delete_suggestion(suggestion_id)
        logger.info(f"Sugerencia eliminada: {suggestion_id}")
