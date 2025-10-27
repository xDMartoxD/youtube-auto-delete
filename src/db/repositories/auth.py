import logging
from typing import Dict, Any, Optional
from src.db.repositories.base import BaseRepository
from src.db.models.auth import TokenModel

logger = logging.getLogger(__name__)


class AuthRepository(BaseRepository[TokenModel]):
    """Repositorio para operaciones de autenticación con DynamoDB."""

    def __init__(self) -> None:
        super().__init__()

    def _prepare_item(self, item: TokenModel) -> Dict[str, Any]:
        """Prepara el modelo de token para DynamoDB."""
        return item.to_item()

    async def get_token_by_sub(self, sub: str) -> Optional[TokenModel]:
        """Obtiene el token de un usuario por su sub."""
        key = {"PK": f"USER#{sub}", "SK": "TOKEN"}
        item = await self.get_item(key)
        if item:
            return TokenModel(**item)
        return None

    async def update_token(
        self, sub: str, token_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Actualiza el token de un usuario."""
        key = {"PK": f"USER#{sub}", "SK": "TOKEN"}

        # Construir expresión de actualización
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}

        for i, (field, value) in enumerate(token_data.items()):
            if i > 0:
                update_expression += ", "
            placeholder = f":val{i}"
            name_placeholder = f"#{field}"
            update_expression += f"{name_placeholder} = {placeholder}"
            expression_attribute_values[placeholder] = value
            expression_attribute_names[name_placeholder] = field

        return await self.update_item(
            key=key,
            update_expression=update_expression,
            expression_attribute_values=expression_attribute_values,
            expression_attribute_names=expression_attribute_names,
        )

    async def delete_token(self, sub: str) -> Optional[Dict[str, Any]]:
        """Elimina el token de un usuario."""
        key = {"PK": f"USER#{sub}", "SK": "TOKEN"}
        return await self.delete_item(key)
