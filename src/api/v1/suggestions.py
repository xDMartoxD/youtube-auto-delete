from fastapi import APIRouter, Depends, status
from src.api.deps import suggestions_service_dependency
from src.schemas.suggestions import (
    SuggestionCreate,
    SuggestionUpdate,
    SuggestionResponse,
    SuggestionListResponse,
)

router = APIRouter()


@router.post(
    "/suggestions",
    status_code=status.HTTP_201_CREATED,
    response_model=SuggestionResponse,
)
async def create_suggestion(
    suggestion_data: SuggestionCreate,
    suggestions_service: suggestions_service_dependency,
) -> SuggestionResponse:
    """
    Crea una nueva sugerencia.

    - **title**: Título de la sugerencia (1-200 caracteres)
    - **description**: Descripción de la sugerencia (1-1000 caracteres)
    """
    return await suggestions_service.create_suggestion(suggestion_data)


@router.get(
    "/suggestions",
    status_code=status.HTTP_200_OK,
    response_model=SuggestionListResponse,
)
async def get_all_suggestions(
    suggestions_service: suggestions_service_dependency,
) -> SuggestionListResponse:
    """Obtiene todas las sugerencias."""
    return await suggestions_service.get_all_suggestions()


@router.get(
    "/suggestions/{suggestion_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuggestionResponse,
)
async def get_suggestion(
    suggestion_id: str,
    suggestions_service: suggestions_service_dependency,
) -> SuggestionResponse:
    """Obtiene una sugerencia por su ID."""
    return await suggestions_service.get_suggestion(suggestion_id)


@router.put(
    "/suggestions/{suggestion_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuggestionResponse,
)
async def update_suggestion(
    suggestion_id: str,
    suggestion_data: SuggestionUpdate,
    suggestions_service: suggestions_service_dependency,
) -> SuggestionResponse:
    """
    Actualiza una sugerencia.

    - **title**: Título de la sugerencia (opcional, 1-200 caracteres)
    - **description**: Descripción de la sugerencia (opcional, 1-1000 caracteres)
    """
    return await suggestions_service.update_suggestion(suggestion_id, suggestion_data)


@router.delete(
    "/suggestions/{suggestion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_suggestion(
    suggestion_id: str,
    suggestions_service: suggestions_service_dependency,
) -> None:
    """Elimina una sugerencia por su ID."""
    await suggestions_service.delete_suggestion(suggestion_id)

