# ...existing code...
from enum import Enum
from typing import Sequence
from mypy_boto3_dynamodb import DynamoDBServiceResource
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.type_defs import (
    KeySchemaElementTypeDef,
    AttributeDefinitionTypeDef,
    CreateTableInputServiceResourceCreateTableTypeDef,
    GlobalSecondaryIndexTypeDef,
)
import boto3
import logging

from src.core.config import config

logger = logging.getLogger(__name__)

dynamodb: DynamoDBServiceResource = boto3.resource(
    "dynamodb",
    region_name=config.aws_region,
    aws_access_key_id=config.aws_access_key_id,
    aws_secret_access_key=config.aws_secret_access_key,
)

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
# ...existing code...
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


def ensure_table():
    """Crea la tabla si no existe, usando configuración desde settings.py"""
    table_name = table_def["TableName"]
    try:
        table = dynamodb.Table(table_name)
        table.load()
        logger.info("Tabla '%s' ya existe.", table_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "ResourceNotFoundException":
            logger.info("⚙️  Creando tabla '%s'...", table_name)
            table = dynamodb.create_table(**table_def)
            table.wait_until_exists()
            logger.info("✅ Tabla '%s' creada correctamente.", table.name)
        else:
            logger.exception("Error comprobando/creando la tabla '%s'", table_name)
            raise


class Types(str, Enum):
    USER = "USER"
    PROFILE = "PROFILE"
    TOKEN = "TOKEN"
    EMAIL = "EMAIL"
    SUGGESTION = "SUGGESTION"
