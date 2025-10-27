# core/main.py
from typing import Any, Callable, Coroutine
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from logging import getLogger
from src.core.logging import setup_logging
from src.core.exceptions import (
    AuthenticationFailedError,
    YoutubeAutoDeleteApiError,
    AwsFailedError,
)
from src.core.lifespan import lifespan
from src.api.v1.auth import router as auth_router
from src.api.v1.health import router as health_router
from src.api.v1.youtube import router as youtube_router


logger = getLogger(__name__)


def create_exception_handler(
    status_code: int, initial_detail: str
) -> Callable[[Request, Exception], Coroutine[Any, Any, JSONResponse]]:

    async def exception_handler(_: Request, exc: Exception) -> JSONResponse:
        # Start from the initial/default message
        message = initial_detail
        user_message = initial_detail
        # If it's our custom error type, extract its fields safely
        if isinstance(exc, YoutubeAutoDeleteApiError):
            if getattr(exc, "message", None):
                message = exc.message
            if getattr(exc, "name", None):
                message = f"{message} [{exc.name}]"
            if getattr(exc, "user_message", None):
                user_message = exc.user_message
        else:
            # Fallback to the exception's string representation
            message = str(exc) or message

        logger.error(exc)
        return JSONResponse(
            status_code=status_code,
            content={"detail": message, "user_message": user_message},
        )

    return exception_handler


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

    # Exceptions
    app.add_exception_handler(
        exc_class_or_status_code=AuthenticationFailedError,
        handler=create_exception_handler(
            status.HTTP_401_UNAUTHORIZED, "The google account is not authorized"
        ),
    )
    app.add_exception_handler(
        exc_class_or_status_code=AwsFailedError,
        handler=create_exception_handler(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Aws client returned an error"
        ),
    )

    app.add_exception_handler(
        exc_class_or_status_code=YoutubeAutoDeleteApiError,
        handler=create_exception_handler(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Youtube Auto Delete API returned an error",
        ),
    )

    # Routers (usar prefijo /api para todos los routes)
    API_PREFIX = "/api"
    app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
    app.include_router(health_router, prefix=f"{API_PREFIX}/health", tags=["health"])
    app.include_router(youtube_router, prefix=f"{API_PREFIX}/youtube", tags=["youtube"])

    return app


app = create_app()
