"""Repository interface for user persistence."""

from abc import ABC, abstractmethod
from typing import Protocol

from src.domain.aggregates.user_aggregate import UserAggregate


class IUserRepository(Protocol):
    """
    Interfaz de repositorio para persistencia de usuarios.
    El dominio define el contrato, la infraestructura lo implementa.
    """

    @abstractmethod
    async def save(self, user: UserAggregate) -> None:
        """Guarda o actualiza un usuario."""
        ...

    @abstractmethod
    async def find_by_id(self, user_id: str) -> UserAggregate | None:
        """Busca un usuario por su ID."""
        ...

    @abstractmethod
    async def find_by_email(self, email: str) -> UserAggregate | None:
        """Busca un usuario por su email."""
        ...

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """Elimina un usuario."""
        ...

