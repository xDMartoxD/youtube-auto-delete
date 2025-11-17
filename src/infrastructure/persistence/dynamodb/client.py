"""DynamoDB client configuration."""

import boto3
from mypy_boto3_dynamodb import DynamoDBServiceResource

from src.core.config import config

dynamodb: DynamoDBServiceResource = boto3.resource(
    "dynamodb",
    region_name=config.aws_region,
    aws_access_key_id=config.aws_access_key_id,
    aws_secret_access_key=config.aws_secret_access_key,
    endpoint_url=config.dynamodb_endpoint,
)
