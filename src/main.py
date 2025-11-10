# core/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logging import getLogger
from src.core.logging import setup_logging
from src.core.exceptions import register_exception_handlers
from src.core.lifespan import lifespan
from src.api.v1.auth import router as auth_router
from src.api.v1.health import router as health_router
from src.api.v1.youtube import router as youtube_router
from src.api.v1.suggestions import router as suggestions_router


logger = getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, title="Youtube Auto Delete API")

    # Setup
    setup_logging()

    # CORS Middleware - DEBE ir antes que los routers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Frontend de desarrollo
            "http://localhost:3000",  # Frontend alternativo
            "http://127.0.0.1:5173",  # Frontend local alternativo
            "http://127.0.0.1:3000",  # Frontend local alternativo
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register all exception handlers using the registry
    register_exception_handlers(app)

    # Routers (usar prefijo /api para todos los routes)
    API_PREFIX = "/api"
    app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
    app.include_router(health_router, prefix=f"{API_PREFIX}/health", tags=["health"])
    app.include_router(youtube_router, prefix=f"{API_PREFIX}/youtube", tags=["youtube"])
    app.include_router(suggestions_router, prefix=f"{API_PREFIX}", tags=["suggestions"])

    return app


app = create_app()
