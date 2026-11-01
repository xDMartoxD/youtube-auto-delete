"""Repository interface for provider connections."""

from typing import Protocol

from src.domain.entities.provider_connection import ProviderConnection
from src.domain.providers.provider_type import ProviderType


class IProviderConnectionRepository(Protocol):
    """Persistence of users' OAuth connections to music providers."""

    async def find(
        self, user_id: str, provider: ProviderType
    ) -> ProviderConnection | None: ...

    async def save(self, connection: ProviderConnection) -> None: ...

    async def delete(self, user_id: str, provider: ProviderType) -> None: ...
