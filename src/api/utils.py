"""Utility functions for API endpoints."""
from typing import Annotated
from fastapi import Query
from datetime import datetime, timezone

from src.schemas.youtube import PaginationParams, PlaylistVideoQueryParams
from src.core.exceptions import InvalidDateRangeError


def parse_date(date_str: str | None) -> datetime | None:
    """Parsea una fecha ISO 8601 de forma robusta."""
    if not date_str:
        return None
    try:
        # Manejar formato con Z (UTC) o sin timezone
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        elif "+" not in date_str and date_str.count("-") >= 3:
            # Si no tiene timezone, asumir UTC
            if "T" in date_str:
                date_str = date_str + "+00:00"
            else:
                date_str = date_str + "T00:00:00+00:00"

        parsed = datetime.fromisoformat(date_str)
        # Asegurar que tiene timezone
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        raise InvalidDateRangeError(
            message=f"Fecha inválida: {date_str}",
            user_message=f"Fecha inválida: {date_str}. Use formato ISO 8601 (ej: 2024-01-01T00:00:00Z o 2024-01-01T00:00:00+00:00)",
        )


def get_pagination_params(
    max_results: Annotated[
        int,
        Query(ge=1, le=50, description="Número máximo de resultados por página"),
    ] = 25,
    page_token: Annotated[
        str | None, Query(description="Token de página para paginación")
    ] = None,
):
    """Dependency para parsear PaginationParams desde query strings."""
    return PaginationParams(max_results=max_results, page_token=page_token)


def get_playlist_video_query_params(
    max_results: Annotated[
        int,
        Query(ge=1, le=50, description="Número máximo de resultados por página"),
    ] = 25,
    page_token: Annotated[
        str | None, Query(description="Token de página para paginación")
    ] = None,
    date_from: Annotated[
        str | None,
        Query(
            description="Fecha de inicio (ISO 8601). Filtra videos agregados desde esta fecha."
        ),
    ] = None,
    date_to: Annotated[
        str | None,
        Query(
            description="Fecha de fin (ISO 8601). Filtra videos agregados hasta esta fecha."
        ),
    ] = None,
) -> PlaylistVideoQueryParams:
    """Dependency para parsear PlaylistVideoQueryParams desde query strings."""
    # Parsear fechas si están presentes
    parsed_date_from = parse_date(date_from) if date_from else None
    parsed_date_to = parse_date(date_to) if date_to else None

    return PlaylistVideoQueryParams(
        max_results=max_results,
        page_token=page_token,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
    )

