"""Domain service for video filtering business rules."""

from datetime import datetime, timezone
from typing import Any

from src.domain.value_objects.date_range import DateRange


class VideoFilterService:
    """Servicio de dominio - contiene SOLO lógica de negocio para filtrado de videos."""

    def filter_by_date_range(
        self,
        items: list[dict[str, Any]],
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[dict[str, Any]]:
        """
        Filtra items de playlist por rango de fechas.
        Filtra por fecha de agregado a la playlist (snippet.publishedAt).

        Regla de negocio: Si un item no tiene fecha de publicación, se excluye.
        """
        if not date_from and not date_to:
            return items

        # Crear DateRange value object si ambas fechas están presentes
        date_range = None
        if date_from and date_to:
            try:
                date_range = DateRange(date_from=date_from, date_to=date_to)
            except ValueError:
                # Si el rango es inválido, retornar lista vacía
                return []

        filtered_items = []

        for item in items:
            if self.should_include_item(item, date_range, date_from, date_to):
                filtered_items.append(item)

        return filtered_items

    def should_include_item(
        self,
        item: dict[str, Any],
        date_range: DateRange | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> bool:
        """
        Determina si un item debe ser incluido según el rango de fechas.
        Regla de negocio: Si no hay filtro de fechas, siempre incluir.
        """
        if not date_from and not date_to:
            return True

        snippet = item.get("snippet", {})
        published_at_str = snippet.get("publishedAt")

        if not published_at_str:
            # Regla de negocio: Si no tiene fecha de publicación, excluir
            return False

        try:
            published_at = datetime.fromisoformat(
                published_at_str.replace("Z", "+00:00")
            )
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            # Si no se puede parsear la fecha, excluir
            return False

        # Usar DateRange si está disponible, sino validar manualmente
        if date_range:
            return date_range.contains(published_at)

        # Validación manual si no hay DateRange completo
        if date_from:
            date_from_utc = date_from
            if date_from_utc.tzinfo is None:
                date_from_utc = date_from_utc.replace(tzinfo=timezone.utc)
            if published_at < date_from_utc:
                return False

        if date_to:
            date_to_utc = date_to
            if date_to_utc.tzinfo is None:
                date_to_utc = date_to_utc.replace(tzinfo=timezone.utc)
            if published_at > date_to_utc:
                return False

        return True

