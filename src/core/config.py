# core/config.py
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import model_validator, Field
from typing import Optional
from enum import Enum

load_dotenv()


class Environment(str, Enum):
    """Entornos disponibles para la aplicación."""

    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"


class BaseConfig(BaseSettings):
    """Configuración base común a todos los entornos."""

    app_env: Environment = Field(
        default=Environment.DEV, description="Entorno de la aplicación"
    )
    cors_origins: str = Field(default="*", description="Orígenes permitidos para CORS")
    table_name: str = Field(
        default="youtube-delete-app", description="Nombre de la tabla DynamoDB"
    )
    jwt_secret: str = Field(default="jwt_secret", description="Secreto para JWT")
    log_level: str = Field(default="INFO", description="Nivel de logging")

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_base_config(self):
        if not self.table_name:
            raise ValueError("table_name must be configured")
        return self


class DevConfig(BaseConfig):
    """Configuración para desarrollo."""

    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    dynamodb_endpoint: str = "http://localhost:8000"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "fakeMyKeyId"
    aws_secret_access_key: str = "fakeSecretAccessKey"
    log_level: str = "DEBUG"


class TestConfig(BaseConfig):
    """Configuración para testing."""

    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    dynamodb_endpoint: str = "http://localhost:8000"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "test_key"
    aws_secret_access_key: str = "test_secret"
    table_name: str = "youtube-delete-app-test"
    log_level: str = "WARNING"


class StagingConfig(BaseConfig):
    """Configuración para staging."""

    google_client_id: str = Field(..., description="Google Client ID for staging")
    google_client_secret: str = Field(
        ..., description="Google Client Secret for staging"
    )
    dynamodb_endpoint: Optional[str] = None  # Usar DynamoDB real
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: str = Field(..., description="AWS Access Key ID")
    aws_secret_access_key: str = Field(..., description="AWS Secret Access Key")
    log_level: str = "INFO"


class ProdConfig(BaseConfig):
    """Configuración para producción."""

    google_client_id: str = Field(..., description="Google Client ID for production")
    google_client_secret: str = Field(
        ..., description="Google Client Secret for production"
    )
    dynamodb_endpoint: Optional[str] = None  # Usar DynamoDB real
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: str = Field(..., description="AWS Access Key ID")
    aws_secret_access_key: str = Field(..., description="AWS Secret Access Key")
    jwt_secret: str = Field(..., description="JWT Secret for production")
    log_level: str = "WARNING"


def get_config() -> BaseConfig:
    """Obtiene la configuración apropiada según el entorno."""
    env = Environment.DEV  # Default

    # Intentar obtener el entorno desde variables de entorno
    import os

    env_str = os.getenv("APP_ENV", "dev")
    try:
        env = Environment(env_str)
    except ValueError:
        print(f"Warning: Invalid environment '{env_str}', using 'dev'")

    config_map = {
        Environment.DEV: DevConfig,
        Environment.TEST: TestConfig,
        Environment.STAGING: StagingConfig,
        Environment.PROD: ProdConfig,
    }

    config_class = config_map[env]
    return config_class()


# Instancia global de configuración
config = get_config()
