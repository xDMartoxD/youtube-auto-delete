# db/models/suggestions.py
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
from src.db.core import Types


@dataclass
class SuggestionModel:
    PK: str
    SK: str
    type: str
    id: str
    title: str
    description: str
    created_at: int
    updated_at: int

    @classmethod
    def create(cls, title: str, description: str) -> "SuggestionModel":
        """Crea una nueva sugerencia."""
        suggestion_id = uuid4().hex
        now = int(datetime.now(timezone.utc).timestamp())

        return cls(
            PK=f"{Types.SUGGESTION.value}#{suggestion_id}",
            SK=f"{Types.SUGGESTION.value}",
            type=Types.SUGGESTION.value,
            id=suggestion_id,
            title=title,
            description=description,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> "SuggestionModel":
        """Crea un modelo desde un item de DynamoDB."""
        return cls(
            PK=item["PK"],
            SK=item["SK"],
            type=item["type"],
            id=item["id"],
            title=item["title"],
            description=item["description"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )

    def to_item(self) -> Dict[str, Any]:
        """Convierte el modelo a un item de DynamoDB."""
        return {
            "PK": self.PK,
            "SK": self.SK,
            "type": self.type,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a un diccionario para respuestas API."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc),
            "updated_at": datetime.fromtimestamp(self.updated_at, tz=timezone.utc),
        }

