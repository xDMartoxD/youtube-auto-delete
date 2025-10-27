# core/lifespan.py
import asyncio
from contextlib import asynccontextmanager
from src.services.google_client import GoogleClient
from src.db.core import ensure_table  # idempotente


@asynccontextmanager
async def lifespan(app):
    # Ejecutar la función síncrona en un hilo para no bloquear el loop
    await asyncio.to_thread(ensure_table)
    google_client = GoogleClient()
    app.state.google_client = google_client
    try:
        yield
    finally:
        await google_client.close()
