"""DynamoDB implementation of IUserRepository."""

import logging
from typing import Dict, Any

from src.domain.aggregates.user_aggregate import UserAggregate
from src.domain.repositories.user_repository import IUserRepository
from src.infrastructure.persistence.base_repository import BaseRepository
from src.infrastructure.persistence.models.token_model import TokenModel
from src.infrastructure.persistence.dynamodb.types import Types
from src.infrastructure.mappers.user_mapper import UserMapper

logger = logging.getLogger(__name__)


class DynamoDBUserRepository(BaseRepository[TokenModel], IUserRepository):
    """DynamoDB implementation of IUserRepository."""

    def __init__(self) -> None:
        super().__init__()

    def _prepare_item(self, item: TokenModel) -> Dict[str, Any]:
        """Prepare TokenModel for DynamoDB."""
        return item.to_item()

    async def save(self, user: UserAggregate) -> None:
        """Save or update a user aggregate."""
        if not user.session:
            raise ValueError("Cannot save user without session")

        # Get existing token model if it exists
        existing_token = await self.get_token_by_sub(user.user_id)
        
        if existing_token:
            # Update existing token
            token_model = UserMapper.to_persistence(user, existing_token)
        else:
            # This shouldn't happen in normal flow - user should be created with TokenModel.from_dto first
            raise ValueError(
                "Cannot save user without existing TokenModel. "
                "Create TokenModel first using from_dto() method."
            )

        await self.insert(token_model)

    async def find_by_id(self, user_id: str) -> UserAggregate | None:
        """Find a user by ID."""
        token_model = await self.get_token_by_sub(user_id)
        if not token_model:
            return None

        # We need email, name, picture from somewhere - they're not in TokenModel
        # In a real implementation, we might need a separate UserProfile table
        # For now, we'll use placeholders and the application layer should provide them
        return UserMapper.to_domain(token_model, email=None, name=None, picture=None)

    async def find_by_email(self, email: str) -> UserAggregate | None:
        """Find a user by email."""
        # TokenModel doesn't store email, so we can't search by email directly
        # This would require a GSI or separate table in a real implementation
        # For now, return None - this method may not be fully implementable with current schema
        logger.warning("find_by_email not fully supported with current TokenModel schema")
        return None

    async def delete(self, user_id: str) -> None:
        """Delete a user."""
        key = {"PK": f"{Types.USER.value}#{user_id}", "SK": Types.TOKEN.value}
        await self.delete_item(key)

    # Helper methods for backward compatibility
    async def get_token_by_sub(self, sub: str) -> TokenModel | None:
        """Get token by user sub (for internal use)."""
        key = {"PK": f"{Types.USER.value}#{sub}", "SK": Types.TOKEN.value}
        item = await self.get_item(key)
        if item:
            return TokenModel(**item)
        return None

    async def insert_token_model(self, token_model: TokenModel) -> None:
        """Insert a new TokenModel (for initial token creation)."""
        await self.insert(token_model)

    async def update_token(self, sub: str, token_data: Dict[str, Any]) -> None:
        """Update token data (for internal use)."""
        key = {"PK": f"{Types.USER.value}#{sub}", "SK": Types.TOKEN.value}

        update_expression = "SET "
        expression_attribute_values: Dict[str, Any] = {}
        expression_attribute_names: Dict[str, str] = {}

        for i, (field, value) in enumerate(token_data.items()):
            if i > 0:
                update_expression += ", "
            placeholder = f":val{i}"
            name_placeholder = f"#{field}"
            update_expression += f"{name_placeholder} = {placeholder}"
            expression_attribute_values[placeholder] = value
            expression_attribute_names[name_placeholder] = field

        await self.update_item(
            key=key,
            update_expression=update_expression,
            expression_attribute_values=expression_attribute_values,
            expression_attribute_names=expression_attribute_names,
        )

