"""DynamoDB implementation of IProviderConnectionRepository."""

from typing import Any

from src.domain.entities.provider_connection import ProviderConnection
from src.domain.providers import ProviderType
from src.domain.repositories.provider_connection_repository import (
    IProviderConnectionRepository,
)
from src.infrastructure.persistence.base_repository import BaseRepository
from src.infrastructure.persistence.dynamodb.types import Types


def _key(user_id: str, provider: ProviderType) -> dict[str, str]:
    # Lives next to the user's other items: PK=USER#<sub>, SK=CONNECTION#<provider>
    return {
        "PK": f"{Types.USER.value}#{user_id}",
        "SK": f"{Types.CONNECTION.value}#{provider}",
    }


class DynamoDBProviderConnectionRepository(
    BaseRepository[ProviderConnection], IProviderConnectionRepository
):
    def _prepare_item(self, item: ProviderConnection) -> dict[str, Any]:
        return {
            **_key(item.user_id, item.provider),
            "type": Types.CONNECTION.value,
            "access_token": item.access_token,
            "refresh_token": item.refresh_token,
            "expires_at": item.expires_at,
            "scope": item.scope,
        }

    async def find(
        self, user_id: str, provider: ProviderType
    ) -> ProviderConnection | None:
        item = await self.get_item(_key(user_id, provider))
        if not item:
            return None
        return ProviderConnection(
            user_id=user_id,
            provider=provider,
            access_token=item["access_token"],
            refresh_token=item["refresh_token"],
            expires_at=int(item["expires_at"]),
            scope=item.get("scope", ""),
        )

    async def save(self, connection: ProviderConnection) -> None:
        await self.insert(connection)

    async def delete(self, user_id: str, provider: ProviderType) -> None:
        await self.delete_item(_key(user_id, provider))
