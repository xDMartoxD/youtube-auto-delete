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
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
        description="Allowed CORS origins (comma-separated list)"
    )

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

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

    # Rate limiting settings
    rate_limit_enabled: bool = Field(
        default=True, description="Enable rate limiting"
    )
    rate_limit_per_minute: int = Field(
        default=60, description="Maximum requests per minute per IP"
    )
    rate_limit_per_hour: int = Field(
        default=1000, description="Maximum requests per hour per IP"
    )

    # Cache TTL settings (in seconds)
    cache_ttl_user_playlists: int = Field(
        default=1800, description="Cache TTL for user playlists (30 minutes)"
    )
    cache_ttl_playlist_videos: int = Field(
        default=3600, description="Cache TTL for playlist videos (1 hour)"
    )
    cache_ttl_playlist_videos_by_date: int = Field(
        default=3600, description="Cache TTL for playlist videos filtered by date (1 hour)"
    )
    cache_ttl_user_profile: int = Field(
        default=3600, description="Cache TTL for user profile (1 hour)"
    )
    cache_ttl_default: int = Field(
        default=3600, description="Default cache TTL (1 hour)"
    )

    model_config = {"env_file": ".env", "extra": "ignore"}


# Global config instance
config = Config()
