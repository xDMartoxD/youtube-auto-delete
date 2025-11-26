"""DynamoDB client configuration."""

from typing import Any
import boto3
from mypy_boto3_dynamodb import DynamoDBServiceResource

from src.core.config import config


def _get_dynamodb_resource_kwargs() -> dict[str, Any]:
    """
    Build boto3 resource kwargs based on environment.

    In development: uses explicit AWS credentials
    In production: relies on IRSA (IAM Roles for Service Accounts) in EKS
    """
    kwargs: dict[str, Any] = {
        "region_name": config.aws_region,
    }

    # Only use explicit credentials in development
    # In production (EKS), use IRSA (IAM Roles for Service Accounts)
    if config.app_env == "dev":
        kwargs["aws_access_key_id"] = config.aws_access_key_id
        kwargs["aws_secret_access_key"] = config.aws_secret_access_key

    # endpoint_url is only used for local DynamoDB
    if config.dynamodb_endpoint:
        kwargs["endpoint_url"] = config.dynamodb_endpoint

    return kwargs


dynamodb: DynamoDBServiceResource = boto3.resource(
    "dynamodb", **_get_dynamodb_resource_kwargs()
)
