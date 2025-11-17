"""DynamoDB-specific persistence code."""

from src.infrastructure.persistence.dynamodb.client import dynamodb
from src.infrastructure.persistence.dynamodb.table import ensure_table
from src.infrastructure.persistence.dynamodb.types import Types

__all__ = ["dynamodb", "ensure_table", "Types"]

