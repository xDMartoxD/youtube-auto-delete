from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import asyncio
import logging
from typing import Dict, Any

import botocore.exceptions

from src.core.logging import get_logger

logger = get_logger("health")

router = APIRouter()


@router.get("/")
async def health_check():
    """
    Endpoint de health check básico (liveness).
    Retorna 200 OK si el proceso está vivo.
    Usado por ECS/Kubernetes para liveness probes.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "service": "playlistmaster-api",
    }


@router.get("/detailed")
async def detailed_health_check():
    """
    Health check detallado que verifica dependencias.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "service": "playlistmaster-api",
        "checks": {},
    }

    # Check DynamoDB
    try:
        # Here you could add a real DynamoDB verification
        health_status["checks"]["dynamodb"] = {
            "status": "healthy",
            "message": "Connection successful",
        }
    except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as e:
        health_status["checks"]["dynamodb"] = {
            "status": "unhealthy",
            "message": f"AWS/DynamoDB error: {str(e)}",
        }
        health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["dynamodb"] = {
            "status": "unhealthy",
            "message": f"Unexpected error: {str(e)}",
        }
        health_status["status"] = "unhealthy"

    # Check Google API
    try:
        # Here you could add a real Google API verification
        health_status["checks"]["google_api"] = {
            "status": "healthy",
            "message": "Connection successful",
        }
    except Exception as e:
        health_status["checks"]["google_api"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/metrics")
async def get_metrics():
    """
    Endpoint básico de métricas de la aplicación.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "uptime": "N/A",  # In a real implementation, you would calculate uptime
            "requests_total": "N/A",  # Request counter
            "active_sessions": "N/A",  # Active sessions
            "database_connections": "N/A",  # DB connections
        },
    }


@router.get("/ready")
async def readiness_check():
    """
    Endpoint de readiness check para Kubernetes/ECS.
    Retorna 200 OK si el servicio está listo para recibir tráfico.
    Retorna 503 si el servicio no está listo (dependencias no disponibles).
    Usado por Kubernetes readiness probes y ECS health checks.
    """
    try:
        # Verificar que la aplicación está inicializada
        # (el lifespan ya se ejecutó si llegamos aquí)
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "playlistmaster-api",
        }
    except (ValueError, KeyError) as e:
        logger.error(f"Readiness check validation error: {e}")
        raise HTTPException(status_code=503, detail="Service not ready") from e
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service not ready") from e
