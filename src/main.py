# core/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logging import getLogger
from src.core.logging import setup_logging
from src.core.exceptions import register_exception_handlers
from src.core.lifespan import lifespan
from src.core.config import config
from src.middlewares.rate_limit import RateLimitMiddleware
from src.api.v1.auth import router as auth_router
from src.api.v1.health import router as health_router
from src.api.v1.youtube import router as youtube_router
from src.api.v1.suggestions import router as suggestions_router
from src.api.v1.providers import router as providers_router


logger = getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, title="Youtube Auto Delete API")

    # Setup
    setup_logging()

    # CORS Middleware - MUST be before routers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Rate Limiting Middleware - must be after CORS but before routers
    app.add_middleware(RateLimitMiddleware)

    # Register all exception handlers using the registry
    register_exception_handlers(app)

    # Routers (use /api prefix for all routes)
    API_PREFIX = "/v1"
    app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
    app.include_router(health_router, prefix=f"{API_PREFIX}/health", tags=["health"])
    app.include_router(youtube_router, prefix=f"{API_PREFIX}/youtube", tags=["youtube"])
    app.include_router(suggestions_router, prefix=f"{API_PREFIX}", tags=["suggestions"])
    app.include_router(
        providers_router, prefix=f"{API_PREFIX}/providers", tags=["providers"]
    )

    return app


app = create_app()
