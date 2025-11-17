"""Domain service for suggestion business rules."""

from src.domain.entities.suggestion import Suggestion
from src.domain.exceptions.domain_exceptions import SuggestionNotFoundDomainException


class SuggestionService:
    """Servicio de dominio - contiene SOLO lógica de negocio para sugerencias."""

    def validate_suggestion_exists(
        self, suggestion: Suggestion | None
    ) -> Suggestion:
        """
        Valida que una sugerencia exista.
        Lanza SuggestionNotFoundDomainException si no existe.
        """
        if suggestion is None:
            raise SuggestionNotFoundDomainException("Suggestion not found")
        return suggestion

    def can_update(self, suggestion: Suggestion) -> bool:
        """
        Verifica si una sugerencia puede ser actualizada.
        Regla de negocio: todas las sugerencias pueden ser actualizadas.
        """
        return True

    def can_delete(self, suggestion: Suggestion) -> bool:
        """
        Verifica si una sugerencia puede ser eliminada.
        Regla de negocio: todas las sugerencias pueden ser eliminadas.
        """
        return True

