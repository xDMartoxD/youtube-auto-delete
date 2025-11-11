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

    # Redis settings
    redis_host: str = Field(
        default="localhost", description="Redis host (local or ElastiCache endpoint)"
    )
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str | None = Field(
        default=None, description="Redis password (required for ElastiCache with auth)"
    )
    redis_url: str | None = Field(
        default=None,
        description="Redis connection URL (recommended for ElastiCache). Format: redis://[password@]host:port or rediss://[password@]host:port (TLS).",
    )
    redis_use_tls: bool = Field(
        default=False,
        description="Use TLS/SSL for Redis connection (required for ElastiCache in-transit encryption)",
    )
    redis_ssl_cert_reqs: str = Field(
        default="required",
        description="SSL certificate requirements: 'none', 'optional', or 'required'",
    )

    model_config = {"env_file": ".env", "extra": "ignore"}


# Global config instance
config = Config()
