"""DynamoDB table definition and management."""

import logging
from typing import Sequence

from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.type_defs import (
    KeySchemaElementTypeDef,
    AttributeDefinitionTypeDef,
    CreateTableInputServiceResourceCreateTableTypeDef,
    GlobalSecondaryIndexTypeDef,
)

from src.core.config import config
from src.infrastructure.persistence.dynamodb.client import dynamodb

logger = logging.getLogger(__name__)

key_schema: Sequence[KeySchemaElementTypeDef] = [
    {"AttributeName": "PK", "KeyType": "HASH"},
    {"AttributeName": "SK", "KeyType": "RANGE"},
]

gsi1_key_schema: Sequence[KeySchemaElementTypeDef] = [
    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
]

gsi2_key_schema: Sequence[KeySchemaElementTypeDef] = [
    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
    {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
]

attributes: Sequence[AttributeDefinitionTypeDef] = [
    {"AttributeName": "PK", "AttributeType": "S"},
    {"AttributeName": "SK", "AttributeType": "S"},
    {"AttributeName": "GSI1PK", "AttributeType": "S"},
    {"AttributeName": "GSI1SK", "AttributeType": "S"},
    {"AttributeName": "GSI2PK", "AttributeType": "S"},
    {"AttributeName": "GSI2SK", "AttributeType": "S"},
]

gsi1: Sequence[GlobalSecondaryIndexTypeDef] = [
    {
        "IndexName": "GSI1",
        "KeySchema": gsi1_key_schema,
        "Projection": {"ProjectionType": "ALL"},
    }
]

gsi2: Sequence[GlobalSecondaryIndexTypeDef] = [
    {
        "IndexName": "GSI2",
        "KeySchema": gsi2_key_schema,
        "Projection": {"ProjectionType": "ALL"},
    }
]

table_def: CreateTableInputServiceResourceCreateTableTypeDef = {
    "TableName": config.table_name,
    "KeySchema": key_schema,
    "AttributeDefinitions": attributes,
    "GlobalSecondaryIndexes": [*gsi1, *gsi2],
    "BillingMode": "PAY_PER_REQUEST",
}


def ensure_table() -> None:
    """
    Crea la tabla si no existe, usando configuración desde config.
    Thread-safe: maneja el caso donde múltiples workers intentan crear la tabla simultáneamente.
    """
    table_name = table_def["TableName"]
    logger.info(
        "🔍 Verificando tabla DynamoDB: '%s' en endpoint: %s",
        table_name,
        config.dynamodb_endpoint or "AWS default",
    )
    try:
        table = dynamodb.Table(table_name)
        table.load()
        logger.info("✅ Tabla '%s' ya existe.", table_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "ResourceNotFoundException":
            logger.info("⚙️  Creando tabla '%s'...", table_name)
            try:
                table = dynamodb.create_table(**table_def)
                table.wait_until_exists()
                logger.info("✅ Tabla '%s' creada correctamente.", table.name)
            except ClientError as create_error:
                create_error_code = create_error.response.get("Error", {}).get("Code")
                # Si otro worker ya está creando la tabla, esperamos a que esté lista
                if create_error_code == "ResourceInUseException":
                    logger.info(
                        "⏳ Tabla '%s' está siendo creada por otro proceso. Esperando...",
                        table_name,
                    )
                    table = dynamodb.Table(table_name)
                    table.wait_until_exists()
                    logger.info("✅ Tabla '%s' está lista (creada por otro proceso).", table_name)
                else:
                    logger.exception(
                        "❌ Error al crear la tabla '%s': %s", table_name, create_error
                    )
                    raise
            except Exception as create_error:
                logger.exception(
                    "❌ Error al crear la tabla '%s': %s", table_name, create_error
                )
                raise
        else:
            logger.exception("❌ Error comprobando/creando la tabla '%s': %s", table_name, e)
            raise
