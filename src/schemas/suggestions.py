from pydantic import BaseModel, Field
from datetime import datetime


class SuggestionCreate(BaseModel):
    """Schema for creating a suggestion."""

    title: str = Field(..., description="Suggestion title", min_length=1, max_length=200)
    description: str = Field(..., description="Suggestion description", min_length=1, max_length=1000)

    model_config = {"extra": "forbid"}


class SuggestionUpdate(BaseModel):
    """Schema for updating a suggestion."""

    title: str | None = Field(None, description="Suggestion title", min_length=1, max_length=200)
    description: str | None = Field(None, description="Suggestion description", min_length=1, max_length=1000)

    model_config = {"extra": "forbid"}


class SuggestionResponse(BaseModel):
    """Response schema for a suggestion."""

    id: str = Field(..., description="Unique suggestion ID")
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Suggestion description")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")

    model_config = {"extra": "forbid"}


class SuggestionListResponse(BaseModel):
    """Response schema for a list of suggestions."""

    items: list[SuggestionResponse] = Field(..., description="List of suggestions")
    total: int = Field(..., description="Total suggestions")

    model_config = {"extra": "forbid"}

