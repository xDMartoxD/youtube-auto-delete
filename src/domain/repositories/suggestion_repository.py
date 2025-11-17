"""Repository interface for suggestion persistence."""

from typing import Protocol

from src.domain.entities.suggestion import Suggestion


class ISuggestionRepository(Protocol):
    """
    Interfaz de repositorio para persistencia de sugerencias.
    El dominio define el contrato, la infraestructura lo implementa.
    """

    async def save(self, suggestion: Suggestion) -> None:
        """Guarda o actualiza una sugerencia."""
        ...

    async def find_by_id(self, suggestion_id: str) -> Suggestion | None:
        """Busca una sugerencia por su ID."""
        ...

    async def find_all(self) -> list[Suggestion]:
        """Obtiene todas las sugerencias."""
        ...

    async def delete(self, suggestion_id: str) -> None:
        """Elimina una sugerencia."""
        ...

