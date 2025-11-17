"""DynamoDB implementation of ISuggestionRepository."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import BeginsWith

from src.domain.entities.suggestion import Suggestion
from src.domain.repositories.suggestion_repository import ISuggestionRepository
from src.infrastructure.persistence.base_repository import BaseRepository
from src.infrastructure.persistence.models.suggestion_model import SuggestionModel
from src.infrastructure.persistence.dynamodb.types import Types
from src.core.exceptions import AwsFailedError
from src.infrastructure.mappers.suggestion_mapper import SuggestionMapper

logger = logging.getLogger(__name__)


class DynamoDBSuggestionRepository(BaseRepository[SuggestionModel], ISuggestionRepository):
    """DynamoDB implementation of ISuggestionRepository."""

    def __init__(self) -> None:
        super().__init__()

    def _prepare_item(self, item: SuggestionModel) -> Dict[str, Any]:
        """Prepare SuggestionModel for DynamoDB."""
        return item.to_item()

    async def save(self, suggestion: Suggestion) -> None:
        """Save or update a suggestion."""
        suggestion_model = SuggestionMapper.to_persistence(suggestion)
        await self.insert(suggestion_model)

    async def find_by_id(self, suggestion_id: str) -> Suggestion | None:
        """Find a suggestion by ID."""
        key = {
            "PK": f"{Types.SUGGESTION.value}#{suggestion_id}",
            "SK": Types.SUGGESTION.value,
        }
        item = await self.get_item(key)
        if item:
            suggestion_model = SuggestionModel.from_item(item)
            return SuggestionMapper.to_domain(suggestion_model)
        return None

    async def find_all(self) -> list[Suggestion]:
        """Get all suggestions."""
        try:
            def _scan():
                filter_expr = BeginsWith("PK", f"{Types.SUGGESTION.value}#")
                response = self.table.scan(FilterExpression=filter_expr)
                return response.get("Items", [])

            items = await asyncio.to_thread(_scan)
            suggestions = []
            for item in items:
                suggestion_model = SuggestionModel.from_item(item)
                suggestions.append(SuggestionMapper.to_domain(suggestion_model))
            return suggestions
        except ClientError as e:
            logger.exception("Error obteniendo todas las sugerencias")
            raise AwsFailedError("failed to get suggestions", "DynamoDB Failed") from e
        except Exception as e:
            logger.exception("Error inesperado obteniendo sugerencias")
            return []

    async def delete(self, suggestion_id: str) -> None:
        """Delete a suggestion."""
        key = {
            "PK": f"{Types.SUGGESTION.value}#{suggestion_id}",
            "SK": Types.SUGGESTION.value,
        }
        await self.delete_item(key)

    # Helper method for updating (used by application layer)
    async def update_suggestion(
        self, suggestion_id: str, update_data: Dict[str, Any]
    ) -> Suggestion | None:
        """Update a suggestion (helper method for application layer)."""
        key = {
            "PK": f"{Types.SUGGESTION.value}#{suggestion_id}",
            "SK": Types.SUGGESTION.value,
        }

        # Add updated_at automatically
        update_data["updated_at"] = int(datetime.now(timezone.utc).timestamp())

        # Build update expression
        update_expression = "SET "
        expression_attribute_values: Dict[str, Any] = {}
        expression_attribute_names: Dict[str, str] = {}

        for i, (field, value) in enumerate(update_data.items()):
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

        # Return updated suggestion
        return await self.find_by_id(suggestion_id)

