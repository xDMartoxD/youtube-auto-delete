from functools import wraps
from typing import Callable, Type, Dict, Any, Coroutine
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.applications import FastAPI
import logging

logger = logging.getLogger(__name__)


class YoutubeAutoDeleteApiError(Exception):
    """Base exception class for the application."""

    def __init__(
        self,
        message: str = "Service is unavailable",
        user_message: str = "Service is unavailable",
    ) -> None:
        self.message = message
        self.user_message = user_message
        super().__init__(self.message)


# Registry to store exceptions and their configurations
exception_registry: Dict[Type[YoutubeAutoDeleteApiError], tuple[int, str]] = {}


def register_exception(
    status_code: int, message: str
) -> Callable[[Type[YoutubeAutoDeleteApiError]], Type[YoutubeAutoDeleteApiError]]:
    """Decorator to register exceptions in the registry."""

    def decorator(
        exception_class: Type[YoutubeAutoDeleteApiError],
    ) -> Type[YoutubeAutoDeleteApiError]:
        # Register the exception in the registry
        exception_registry[exception_class] = (status_code, message)
        return exception_class

    return decorator


def create_exception_handler(
    status_code: int, initial_detail: str
) -> Callable[[Request, Exception], Coroutine[Any, Any, JSONResponse]]:
    """Creates a generic exception handler."""

    async def exception_handler(_: Request, exc: Exception) -> JSONResponse:
        # Start from the initial/default message
        message = initial_detail
        user_message = initial_detail

        # If it's our custom error type, extract its fields safely
        if isinstance(exc, YoutubeAutoDeleteApiError):
            exc_message = getattr(exc, "message", None)

            exc_user_message = getattr(exc, "user_message", None)

            if exc_message:
                message = exc_message
            if exc_user_message:
                user_message = exc_user_message
        else:
            exc_message = getattr(exc, "message", None)
            if exc_message:
                message = exc_message
            else:
                # Fallback to the exception's string representation
                message = str(exc) or message

        logger.error(exc)
        return JSONResponse(
            status_code=status_code,
            content={"detail": message, "user_message": user_message},
        )

    return exception_handler


def register_exception_handlers(app: FastAPI) -> None:
    """Registers all exception handlers using the registry."""
    for exception_class, (status_code, message) in exception_registry.items():
        app.add_exception_handler(
            exc_class_or_status_code=exception_class,
            handler=create_exception_handler(status_code, message),
        )


# Define exceptions with decorators
@register_exception(
    status.HTTP_401_UNAUTHORIZED, "The google account is not authorized"
)
class AuthenticationFailedError(YoutubeAutoDeleteApiError):
    """Invalid auth credentials"""

    pass


@register_exception(status.HTTP_503_SERVICE_UNAVAILABLE, "AWS client returned an error")
class AwsFailedError(YoutubeAutoDeleteApiError):
    """AWS service error"""

    pass


@register_exception(status.HTTP_400_BAD_REQUEST, "Invalid date range parameters")
class InvalidDateRangeError(YoutubeAutoDeleteApiError):
    """Invalid date range parameters"""

    pass


@register_exception(404, "Suggestion not found")
class SuggestionNotFoundError(YoutubeAutoDeleteApiError):
    """Suggestion not found."""

    pass


@register_exception(500, "Failed to logout user")
class LogoutFailedError(YoutubeAutoDeleteApiError):
    """Failed to logout user"""

    pass


@register_exception(404, "Provider not supported")
class ProviderNotSupportedError(YoutubeAutoDeleteApiError):
    """The requested provider is not available."""

    pass


@register_exception(404, "Playlist not found")
class PlaylistNotFoundError(YoutubeAutoDeleteApiError):
    """Playlist not found on the provider."""

    pass


@register_exception(status.HTTP_400_BAD_REQUEST, "Invalid playlist operation")
class InvalidPlaylistOperationError(YoutubeAutoDeleteApiError):
    """The playlist operation breaks a business rule."""

    pass


@register_exception(status.HTTP_502_BAD_GATEWAY, "The music provider returned an error")
class ProviderRequestError(YoutubeAutoDeleteApiError):
    """Call to an external provider failed."""

    pass
