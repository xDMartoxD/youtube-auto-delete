import logging
from typing import Dict, Any, Optional, List
from src.db.repositories.base import BaseRepository
from src.db.models.suggestions import SuggestionModel
from src.db.core import Types

logger = logging.getLogger(__name__)


class SuggestionsRepository(BaseRepository[SuggestionModel]):
    """Repositorio para operaciones de sugerencias con DynamoDB."""

    def __init__(self) -> None:
        super().__init__()

    def _prepare_item(self, item: SuggestionModel) -> Dict[str, Any]:
        """Prepara el modelo de sugerencia para DynamoDB."""
        return item.to_item()

    async def get_by_id(self, suggestion_id: str) -> Optional[SuggestionModel]:
        """Obtiene una sugerencia por su ID."""
        key = {"PK": f"{Types.SUGGESTION.value}#{suggestion_id}", "SK": Types.SUGGESTION.value}
        item = await self.get_item(key)
        if item:
            return SuggestionModel.from_item(item)
        return None

    async def get_all(self) -> List[SuggestionModel]:
        """Obtiene todas las sugerencias usando scan."""
        import asyncio
        from botocore.exceptions import ClientError
        from boto3.dynamodb.conditions import BeginsWith
        from src.core.exceptions import AwsFailedError

        try:
            def _scan():
                # Usar FilterExpression con boto3.dynamodb.conditions
                filter_expr = BeginsWith("PK", f"{Types.SUGGESTION.value}#")
                response = self.table.scan(FilterExpression=filter_expr)
                return response.get("Items", [])

            items = await asyncio.to_thread(_scan)
            return [SuggestionModel.from_item(item) for item in items]
        except ClientError as e:
            logger.exception("Error obteniendo todas las sugerencias")
            raise AwsFailedError("failed to get suggestions", "DynamoDB Failed") from e
        except Exception as e:
            logger.exception("Error inesperado obteniendo sugerencias")
            return []

    async def update_suggestion(
        self, suggestion_id: str, update_data: Dict[str, Any]
    ) -> Optional[SuggestionModel]:
        """Actualiza una sugerencia."""
        key = {"PK": f"{Types.SUGGESTION.value}#{suggestion_id}", "SK": Types.SUGGESTION.value}

        # Agregar updated_at automáticamente
        from datetime import datetime, timezone
        update_data["updated_at"] = int(datetime.now(timezone.utc).timestamp())

        # Construir expresión de actualización
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}

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

        # Retornar la sugerencia actualizada
        return await self.get_by_id(suggestion_id)

    async def delete_suggestion(self, suggestion_id: str) -> Optional[Dict[str, Any]]:
        """Elimina una sugerencia."""
        key = {"PK": f"{Types.SUGGESTION.value}#{suggestion_id}", "SK": Types.SUGGESTION.value}
        return await self.delete_item(key)

