"""Entidad de dominio para Suggestion."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self
from uuid import uuid4


@dataclass(slots=True, frozen=False)
class Suggestion:
    """Entidad de dominio - representa una sugerencia."""

    id: str
    title: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, title: str, description: str) -> Self:
        """Crea una nueva sugerencia."""
        suggestion_id = uuid4().hex
        now = datetime.now(timezone.utc)

        return cls(
            id=suggestion_id,
            title=title.strip(),
            description=description.strip(),
            created_at=now,
            updated_at=now,
        )

    def update_title(self, new_title: str) -> None:
        """Actualiza el título de la sugerencia."""
        if not new_title or len(new_title.strip()) == 0:
            raise ValueError("El título no puede estar vacío")
        if len(new_title) > 200:
            raise ValueError("El título no puede exceder 200 caracteres")
        self.title = new_title.strip()
        self.updated_at = datetime.now(timezone.utc)

    def update_description(self, new_description: str) -> None:
        """Actualiza la descripción de la sugerencia."""
        if not new_description or len(new_description.strip()) == 0:
            raise ValueError("La descripción no puede estar vacía")
        if len(new_description) > 1000:
            raise ValueError("La descripción no puede exceder 1000 caracteres")
        self.description = new_description.strip()
        self.updated_at = datetime.now(timezone.utc)

    def update(self, title: str | None = None, description: str | None = None) -> None:
        """Actualiza los campos de la sugerencia."""
        if title is not None:
            self.update_title(title)
        if description is not None:
            self.update_description(description)

