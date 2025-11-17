"""Base repository for DynamoDB operations."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar, Generic

from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.type_defs import (
    PutItemOutputTableTypeDef,
    UpdateItemOutputTableTypeDef,
    DeleteItemOutputTableTypeDef,
)
import boto3

from src.core.config import config
from src.core.exceptions import AwsFailedError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Repositorio base con funcionalidades comunes para DynamoDB."""

    def __init__(self, table_name: str | None = None) -> None:
        self.table_name = table_name or config.table_name
        self._dynamodb = boto3.resource(
            "dynamodb",
            region_name=config.aws_region,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
        self.table = self._dynamodb.Table(self.table_name)

    async def insert(self, item: T) -> PutItemOutputTableTypeDef | None:
        """Inserta un ítem de forma asíncrona."""
        payload = self._prepare_item(item)

        try:
            # Ejecutar operación síncrona en thread para no bloquear
            put_item_response = await asyncio.to_thread(
                self.table.put_item, Item=payload
            )
            logger.debug(
                "Inserted item into table %s PK=%s SK=%s",
                self.table_name,
                payload.get("PK"),
                payload.get("SK"),
            )
            return put_item_response
        except ClientError as e:
            logger.exception("DynamoDB put_item failed for table %s", self.table_name)
            raise AwsFailedError("failed to put new item", "DynamoDB Failed") from e

    async def get_item(self, key: Dict[str, Any]) -> Dict[str, Any] | None:
        """Obtiene un ítem por su clave primaria."""
        try:
            response = await asyncio.to_thread(self.table.get_item, Key=key)
            return response.get("Item")
        except ClientError as e:
            logger.exception("DynamoDB get_item failed for table %s", self.table_name)
            raise AwsFailedError("failed to get item", "DynamoDB Failed") from e

    async def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Dict[str, str] | None = None,
    ) -> UpdateItemOutputTableTypeDef:
        """Actualiza un ítem existente."""
        try:
            kwargs = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_attribute_values,
            }
            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            response = await asyncio.to_thread(self.table.update_item, **kwargs)
            return response
        except ClientError as e:
            logger.exception(
                "DynamoDB update_item failed for table %s", self.table_name
            )
            raise AwsFailedError("failed to update item", "DynamoDB Failed") from e

    async def delete_item(self, key: Dict[str, Any]) -> DeleteItemOutputTableTypeDef:
        """Elimina un ítem por su clave primaria."""
        try:
            response = await asyncio.to_thread(self.table.delete_item, Key=key)
            return response
        except ClientError as e:
            logger.exception(
                "DynamoDB delete_item failed for table %s", self.table_name
            )
            raise AwsFailedError("failed to delete item", "DynamoDB Failed") from e

    @abstractmethod
    def _prepare_item(self, item: T) -> Dict[str, Any]:
        """
        Prepara el ítem para ser insertado en DynamoDB.
        Debe ser implementado por las clases hijas.
        """
        pass

    async def batch_write(self, items: list[T]) -> Dict[str, Any] | None:
        """Escribe múltiples ítems en lote."""
        if not items:
            return None

        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    payload = self._prepare_item(item)
                    batch.put_item(Item=payload)

            logger.debug(
                "Batch wrote %d items to table %s", len(items), self.table_name
            )
            return {"processed": len(items)}
        except ClientError as e:
            logger.exception(
                "DynamoDB batch_write failed for table %s", self.table_name
            )
            raise AwsFailedError(
                "failed to batch write items", "DynamoDB Failed"
            ) from e
