import logging
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime
import traceback


class StructuredFormatter(logging.Formatter):
    """Formateador que produce logs estructurados en JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Agregar información adicional si está disponible
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation

        # Agregar excepción si está presente
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Agregar campos extra
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ContextFilter(logging.Filter):
    """Filtro que agrega contexto a los logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Agregar información del entorno si está disponible
        record.environment = getattr(record, "environment", "unknown")
        return True


def setup_logging(level: int = logging.INFO, fmt: str | None = None) -> None:
    """
    Configura el sistema de logging estructurado para la aplicación.
    """
    # Configurar el handler para stdout con formato JSON
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Usar nuestro formateador estructurado
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)

    # Agregar filtro de contexto
    context_filter = ContextFilter()
    handler.addFilter(context_filter)

    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Configurar loggers específicos con niveles apropiados
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    # Logger específico para la aplicación
    app_logger = logging.getLogger("youtube_auto_delete")
    app_logger.setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger con el nombre especificado."""
    return logging.getLogger(f"youtube_auto_delete.{name}")


def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """Registra un mensaje con contexto adicional."""
    extra = {**context}
    logger.log(level, message, extra=extra)
