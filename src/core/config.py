# core/config.py
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

load_dotenv()


class Config(BaseSettings):
    """Simplified configuration for the application."""

    # App settings
    app_env: str = Field(default="dev", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database settings
    table_name: str = Field(
        default="youtube-delete-app", description="DynamoDB table name"
    )
    dynamodb_endpoint: str | None = Field(
        default="http://localhost:8000", description="DynamoDB endpoint"
    )
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: str = Field(default="fakeMyKeyId", description="AWS access key")
    aws_secret_access_key: str = Field(
        default="fakeSecretAccessKey", description="AWS secret key"
    )

    # Google OAuth settings
    google_client_id: str | None = Field(
        default=None, description="Google OAuth client ID"
    )
    google_client_secret: str | None = Field(
        default=None, description="Google OAuth client secret"
    )

    # JWT settings
    jwt_secret: str = Field(default="jwt_secret", description="JWT secret key")

    # CORS settings
    cors_origins: str = Field(default="*", description="Allowed CORS origins")

    model_config = {"env_file": ".env", "extra": "ignore"}


# Global config instance
config = Config()
