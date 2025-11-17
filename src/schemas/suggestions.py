from pydantic import BaseModel, Field
from datetime import datetime


class SuggestionCreate(BaseModel):
    """Schema para crear una sugerencia."""

    title: str = Field(..., description="Título de la sugerencia", min_length=1, max_length=200)
    description: str = Field(..., description="Descripción de la sugerencia", min_length=1, max_length=1000)

    model_config = {"extra": "forbid"}


class SuggestionUpdate(BaseModel):
    """Schema para actualizar una sugerencia."""

    title: str | None = Field(None, description="Título de la sugerencia", min_length=1, max_length=200)
    description: str | None = Field(None, description="Descripción de la sugerencia", min_length=1, max_length=1000)

    model_config = {"extra": "forbid"}


class SuggestionResponse(BaseModel):
    """Schema de respuesta para una sugerencia."""

    id: str = Field(..., description="ID único de la sugerencia")
    title: str = Field(..., description="Título de la sugerencia")
    description: str = Field(..., description="Descripción de la sugerencia")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    model_config = {"extra": "forbid"}


class SuggestionListResponse(BaseModel):
    """Schema de respuesta para una lista de sugerencias."""

    items: list[SuggestionResponse] = Field(..., description="Lista de sugerencias")
    total: int = Field(..., description="Total de sugerencias")

    model_config = {"extra": "forbid"}

