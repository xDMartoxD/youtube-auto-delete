"""DynamoDB entity types enum."""

from enum import StrEnum


class Types(StrEnum):
    """Enum for DynamoDB entity types using Python 3.13 StrEnum."""

    USER = "USER"
    PROFILE = "PROFILE"
    TOKEN = "TOKEN"
    EMAIL = "EMAIL"
    SUGGESTION = "SUGGESTION"
