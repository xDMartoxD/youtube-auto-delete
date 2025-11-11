# core/lifespan.py
import asyncio
import logging
from contextlib import asynccontextmanager
from src.services.google_client import GoogleClient
from src.db.core import ensure_table  # idempotente
from src.core.cache import get_redis_client, close_redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    # Ejecutar la función síncrona en un hilo para no bloquear el loop
    await asyncio.to_thread(ensure_table)

    # Inicializar Google Client
    google_client = GoogleClient()
    app.state.google_client = google_client

    # Inicializar Redis client
    logger.info("Attempting to connect to Redis...")
    try:
        redis_client = await get_redis_client()
        logger.debug("Redis client created, testing connection with ping()...")
        # Test connection - ping() returns True if connection is OK
        result = await redis_client.ping()  # type: ignore[awaitable-is-bool]
        logger.info(f"✅ Redis connection established - ping result: {result}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}. Cache will not be available.", exc_info=True)

    try:
        yield
    finally:
        await google_client.close()
        await close_redis_client()
