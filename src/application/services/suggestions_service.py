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
    NO contiene lógica de negocio, solo orquesta.
    """

    def __init__(
        self,
        suggestion_repo: ISuggestionRepository,
        suggestion_service: SuggestionService | None = None,
    ):
        self.suggestion_repo = suggestion_repo
        self.suggestion_service = suggestion_service or SuggestionService()

    def _to_response(self, suggestion: Suggestion) -> SuggestionResponse:
        """Convierte una entidad de dominio a un schema de respuesta."""
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
        """Crea una nueva sugerencia."""
        # DOMINIO: Crear entidad
        suggestion = Suggestion.create(
            title=suggestion_data.title,
            description=suggestion_data.description,
        )

        # INFRAESTRUCTURA: Guardar en base de datos
        await self.suggestion_repo.save(suggestion)

        # DOMINIO: Raise domain event
        event = SuggestionCreated(
            suggestion_id=suggestion.id,
            title=suggestion.title,
        )
        logger.info(f"Domain event: {event}")

        logger.info(f"Sugerencia creada: {suggestion.id}")
        return self._to_response(suggestion)

    async def get_suggestion(self, suggestion_id: str) -> SuggestionResponse:
        """Obtiene una sugerencia por su ID."""
        # INFRAESTRUCTURA: Obtener de base de datos
        suggestion = await self.suggestion_repo.find_by_id(suggestion_id)

        # DOMINIO: Validar que existe (puede lanzar SuggestionNotFoundDomainException)
        try:
            suggestion = self.suggestion_service.validate_suggestion_exists(suggestion)
        except SuggestionNotFoundDomainException as e:
            # Mapear excepción de dominio a excepción de aplicación
            raise SuggestionNotFoundError(
                message=str(e.message),
                user_message="Sugerencia no encontrada",
            ) from e

        return self._to_response(suggestion)

    async def get_all_suggestions(self) -> SuggestionListResponse:
        """Obtiene todas las sugerencias."""
        # INFRAESTRUCTURA: Obtener de base de datos
        suggestions = await self.suggestion_repo.find_all()

        suggestion_responses = [self._to_response(s) for s in suggestions]

        return SuggestionListResponse(
            items=suggestion_responses,
            total=len(suggestion_responses),
        )

    async def update_suggestion(
        self, suggestion_id: str, suggestion_data: SuggestionUpdate
    ) -> SuggestionResponse:
        """Actualiza una sugerencia."""
        # INFRAESTRUCTURA: Obtener de base de datos
        suggestion = await self.suggestion_repo.find_by_id(suggestion_id)

        # DOMINIO: Validar que existe (puede lanzar SuggestionNotFoundDomainException)
        try:
            suggestion = self.suggestion_service.validate_suggestion_exists(suggestion)
        except SuggestionNotFoundDomainException as e:
            # Mapear excepción de dominio a excepción de aplicación
            raise SuggestionNotFoundError(
                message=str(e.message),
                user_message="Sugerencia no encontrada",
            ) from e

        # DOMINIO: Validar que puede actualizarse
        if not self.suggestion_service.can_update(suggestion):
            raise ValueError("La sugerencia no puede ser actualizada")

        # DOMINIO: Actualizar entidad
        if suggestion_data.title is not None or suggestion_data.description is not None:
            suggestion.update(
                title=suggestion_data.title,
                description=suggestion_data.description,
            )

            # INFRAESTRUCTURA: Guardar cambios
            await self.suggestion_repo.save(suggestion)

        logger.info(f"Sugerencia actualizada: {suggestion_id}")
        return self._to_response(suggestion)

    async def delete_suggestion(self, suggestion_id: str) -> None:
        """Elimina una sugerencia."""
        # INFRAESTRUCTURA: Obtener de base de datos
        suggestion = await self.suggestion_repo.find_by_id(suggestion_id)

        # DOMINIO: Validar que existe y puede eliminarse (puede lanzar SuggestionNotFoundDomainException)
        try:
            suggestion = self.suggestion_service.validate_suggestion_exists(suggestion)
        except SuggestionNotFoundDomainException as e:
            # Mapear excepción de dominio a excepción de aplicación
            raise SuggestionNotFoundError(
                message=str(e.message),
                user_message="Sugerencia no encontrada",
            ) from e
        if not self.suggestion_service.can_delete(suggestion):
            raise ValueError("La sugerencia no puede ser eliminada")

        # INFRAESTRUCTURA: Eliminar de base de datos
        await self.suggestion_repo.delete(suggestion_id)
        logger.info(f"Sugerencia eliminada: {suggestion_id}")

